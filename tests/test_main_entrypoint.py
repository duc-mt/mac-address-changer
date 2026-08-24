"""Tests for main.main().

Covers the top-level orchestration: the ifconfig-availability check,
interface validation, the automatic once-only backup, and the
before/after change verification.
"""

from __future__ import annotations

from unittest import mock

import pytest

import main


def test_missing_ifconfig_exits_cleanly_with_a_clear_message(capsys):
    """Regression test: on a system without ifconfig installed
    (increasingly common - many modern Linux distributions no longer
    ship net-tools by default), this used to crash with an unhandled
    FileNotFoundError instead of a clear message."""
    with mock.patch('main.shutil.which', return_value=None), \
         pytest.raises(SystemExit) as exc_info:
        main.main()

    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert 'ifconfig was not found' in out


def test_nonexistent_interface_exits_cleanly_with_available_list(capsys):
    """Regression test: the interface name typed at "What is the
    network interface?" used to never be validated at all - a typo
    only surfaced as ifconfig's own cryptic error partway through
    change_mac()."""
    with mock.patch('main.shutil.which', return_value='/sbin/ifconfig'), \
         mock.patch('builtins.input', return_value='no-such-interface'), \
         mock.patch('main.get_interface_mac', return_value=None), \
         mock.patch('main.list_interfaces', return_value=['eth0', 'lo']), \
         mock.patch('main.change_mac') as mock_change_mac, \
         pytest.raises(SystemExit) as exc_info:
        main.main()

    assert exc_info.value.code == 1
    mock_change_mac.assert_not_called()
    out = capsys.readouterr().out
    assert 'No such interface' in out
    assert 'eth0, lo' in out


def test_interface_name_input_is_trimmed():
    inputs = iter([' eth0 ', '2'])
    with mock.patch('main.shutil.which', return_value='/sbin/ifconfig'), \
         mock.patch('builtins.input', lambda *a: next(inputs)), \
         mock.patch(
             'main.get_interface_mac', return_value='11:22:33:44:55:66'
         ) as mock_get_mac, \
         mock.patch('main.read_backup', return_value={}), \
         mock.patch('main.write_backup'), \
         mock.patch('main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'), \
         mock.patch('main.change_mac', return_value=True):
        main.main()

    mock_get_mac.assert_any_call('eth0')  # not ' eth0 '


class TestAutomaticBackup:
    def test_first_time_seeing_an_interface_backs_it_up(self, capsys):
        inputs = iter(['eth0', '2'])
        with mock.patch('main.shutil.which', return_value='/sbin/ifconfig'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.get_interface_mac', return_value='11:22:33:44:55:66'
             ), \
             mock.patch('main.read_backup', return_value={}), \
             mock.patch('main.write_backup') as mock_write_backup, \
             mock.patch(
                 'main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'
             ), \
             mock.patch('main.change_mac', return_value=True):
            main.main()

        mock_write_backup.assert_called_once_with(
            main.BACKUP_FILE, 'eth0', '11:22:33:44:55:66'
        )
        assert 'Backed up' in capsys.readouterr().out

    def test_an_already_backed_up_interface_is_not_backed_up_again(
        self, capsys
    ):
        """Regression-guarding test: if this ran unconditionally on
        every invocation, a second change to the same interface would
        silently overwrite the one backup that actually mattered - the
        *true* original MAC - with an already-changed value."""
        inputs = iter(['eth0', '2'])
        with mock.patch('main.shutil.which', return_value='/sbin/ifconfig'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.get_interface_mac', return_value='aa:aa:aa:aa:aa:aa'
             ), \
             mock.patch(
                 'main.read_backup',
                 return_value={'eth0': '11:22:33:44:55:66'},
             ), \
             mock.patch('main.write_backup') as mock_write_backup, \
             mock.patch(
                 'main.random_new_mac', return_value='bb:bb:bb:bb:bb:bb'
             ), \
             mock.patch('main.change_mac', return_value=True):
            main.main()

        mock_write_backup.assert_not_called()
        assert 'Backed up' not in capsys.readouterr().out


class TestChangeVerification:
    def test_successful_change_is_verified_against_the_new_mac(self, capsys):
        """Regression test: previously "success" meant only "ifconfig's
        exit code was 0" - the script never actually confirmed the
        interface's MAC had changed to the intended value."""
        inputs = iter(['eth0', '2'])
        with mock.patch('main.shutil.which', return_value='/sbin/ifconfig'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'
             ), \
             mock.patch(
                 'main.get_interface_mac',
                 side_effect=['11:22:33:44:55:66', 'aa:bb:cc:dd:ee:ff'],
             ), \
             mock.patch('main.read_backup', return_value={}), \
             mock.patch('main.write_backup'), \
             mock.patch('main.change_mac', return_value=True):
            main.main()

        out = capsys.readouterr().out
        assert 'from 11:22:33:44:55:66 to aa:bb:cc:dd:ee:ff' in out
        assert 'Success' in out

    def test_mismatch_after_change_is_reported_not_silently_trusted(
        self, capsys
    ):
        inputs = iter(['eth0', '2'])
        with mock.patch('main.shutil.which', return_value='/sbin/ifconfig'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'
             ), \
             mock.patch(
                 'main.get_interface_mac',
                 side_effect=['11:22:33:44:55:66', '11:22:33:44:55:66'],
             ), \
             mock.patch('main.read_backup', return_value={}), \
             mock.patch('main.write_backup'), \
             mock.patch('main.change_mac', return_value=True):
            main.main()

        out = capsys.readouterr().out
        assert 'double check' in out

    def test_failed_change_mac_prints_no_success_message(self, capsys):
        inputs = iter(['eth0', '2'])
        with mock.patch('main.shutil.which', return_value='/sbin/ifconfig'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'
             ), \
             mock.patch(
                 'main.get_interface_mac', return_value='11:22:33:44:55:66'
             ), \
             mock.patch('main.read_backup', return_value={}), \
             mock.patch('main.write_backup'), \
             mock.patch('main.change_mac', return_value=False):
            main.main()

        out = capsys.readouterr().out
        assert 'Success' not in out
