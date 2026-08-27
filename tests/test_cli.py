"""Tests for the non-interactive CLI mode (main.run_cli(), reached via
main.main() with a mocked sys.argv - the way a person would actually
invoke `python main.py --interface ... --mode ...` from a shell).
"""

from __future__ import annotations

from unittest import mock

import pytest

import main


def run_main(argv, tool='ip'):
    with mock.patch('sys.argv', ['main.py', *argv]), \
         mock.patch('main.detect_network_tool', return_value=tool):
        return main.main()


class TestManualMode:
    def test_changes_to_the_given_mac(self, capsys):
        with mock.patch(
            'main.get_interface_mac',
            side_effect=['11:22:33:44:55:66', 'aa:bb:cc:dd:ee:ff'],
        ), mock.patch('main.read_backup', return_value={}), \
           mock.patch('main.write_backup'), \
           mock.patch('main.append_history'), \
           mock.patch('main.change_mac', return_value=True):
            exit_code = run_main([
                '--interface', 'eth0', '--mode', 'manual',
                '--mac', 'aa:bb:cc:dd:ee:ff',
            ])

        assert exit_code == 0
        assert 'Success' in capsys.readouterr().out

    def test_missing_mac_is_an_error(self):
        with mock.patch(
            'main.get_interface_mac', return_value='11:22:33:44:55:66'
        ), pytest.raises(SystemExit) as exc_info:
            run_main(['--interface', 'eth0', '--mode', 'manual'])
        assert exc_info.value.code == 2

    def test_invalid_mac_is_an_error(self):
        with mock.patch(
            'main.get_interface_mac', return_value='11:22:33:44:55:66'
        ), pytest.raises(SystemExit) as exc_info:
            run_main([
                '--interface', 'eth0', '--mode', 'manual',
                '--mac', 'not-a-mac',
            ])
        assert exc_info.value.code == 2


class TestRandomMode:
    def test_changes_to_a_random_mac(self, capsys):
        with mock.patch(
            'main.get_interface_mac',
            side_effect=['11:22:33:44:55:66', 'aa:bb:cc:dd:ee:ff'],
        ), mock.patch('main.read_backup', return_value={}), \
           mock.patch('main.write_backup'), \
           mock.patch('main.append_history'), \
           mock.patch(
               'main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'
           ), mock.patch('main.change_mac', return_value=True):
            exit_code = run_main(['--interface', 'eth0', '--mode', 'random'])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert 'aa:bb:cc:dd:ee:ff' in out


class TestRestoreMode:
    def test_restores_the_backed_up_original(self, capsys):
        with mock.patch(
            'main.get_interface_mac',
            side_effect=['aa:aa:aa:aa:aa:aa', '11:22:33:44:55:66'],
        ), mock.patch(
            'main.read_backup', return_value={'eth0': '11:22:33:44:55:66'}
        ), mock.patch('main.write_backup'), \
           mock.patch('main.append_history'), \
           mock.patch('main.change_mac', return_value=True):
            exit_code = run_main(['--interface', 'eth0', '--mode', 'restore'])

        assert exit_code == 0
        assert '11:22:33:44:55:66' in capsys.readouterr().out

    def test_no_backup_is_an_error(self):
        with mock.patch(
            'main.get_interface_mac', return_value='aa:aa:aa:aa:aa:aa'
        ), mock.patch('main.read_backup', return_value={}), \
           pytest.raises(SystemExit) as exc_info:
            run_main(['--interface', 'eth0', '--mode', 'restore'])
        assert exc_info.value.code == 2


class TestUndoMode:
    def test_undoes_to_the_most_recent_history_entry(self, capsys):
        with mock.patch(
            'main.get_interface_mac',
            side_effect=['bb:bb:bb:bb:bb:bb', 'aa:aa:aa:aa:aa:aa'],
        ), mock.patch('main.read_backup', return_value={}), \
           mock.patch(
               'main.read_history',
               return_value={'eth0': ['11:22:33:44:55:66', 'aa:aa:aa:aa:aa:aa']},
           ), mock.patch('main.write_backup'), \
           mock.patch('main.pop_last_history') as mock_pop, \
           mock.patch('main.append_history') as mock_append, \
           mock.patch('main.change_mac', return_value=True):
            exit_code = run_main(['--interface', 'eth0', '--mode', 'undo'])

        assert exit_code == 0
        assert 'aa:aa:aa:aa:aa:aa' in capsys.readouterr().out
        mock_pop.assert_called_once_with(main.HISTORY_FILE, 'eth0')
        mock_append.assert_not_called()

    def test_no_history_is_an_error(self):
        with mock.patch(
            'main.get_interface_mac', return_value='aa:aa:aa:aa:aa:aa'
        ), mock.patch('main.read_backup', return_value={}), \
           mock.patch('main.read_history', return_value={}), \
           pytest.raises(SystemExit) as exc_info:
            run_main(['--interface', 'eth0', '--mode', 'undo'])
        assert exc_info.value.code == 2


class TestDryRun:
    def test_makes_no_changes(self, capsys):
        with mock.patch(
            'main.get_interface_mac', return_value='11:22:33:44:55:66'
        ), mock.patch('main.read_backup', return_value={}), \
           mock.patch('main.write_backup') as mock_write_backup, \
           mock.patch('main.append_history') as mock_append_history, \
           mock.patch('main.change_mac') as mock_change_mac:
            exit_code = run_main([
                '--interface', 'eth0', '--mode', 'manual',
                '--mac', 'aa:bb:cc:dd:ee:ff', '--dry-run',
            ])

        assert exit_code == 0
        mock_change_mac.assert_not_called()
        mock_write_backup.assert_not_called()
        mock_append_history.assert_not_called()
        assert 'DRY RUN' in capsys.readouterr().out

    def test_shows_what_would_change(self, capsys):
        with mock.patch(
            'main.get_interface_mac', return_value='11:22:33:44:55:66'
        ), mock.patch('main.read_backup', return_value={}):
            run_main([
                '--interface', 'eth0', '--mode', 'manual',
                '--mac', 'aa:bb:cc:dd:ee:ff', '--dry-run',
            ])

        out = capsys.readouterr().out
        assert '11:22:33:44:55:66' in out
        assert 'aa:bb:cc:dd:ee:ff' in out


class TestInterfaceValidation:
    def test_nonexistent_interface_is_an_error_with_available_list(self):
        with mock.patch('main.get_interface_mac', return_value=None), \
             mock.patch(
                 'main.list_interfaces', return_value=['eth0', 'lo']
             ), pytest.raises(SystemExit) as exc_info:
            run_main([
                '--interface', 'no-such-interface', '--mode', 'random',
            ])
        assert exc_info.value.code == 2


class TestVerification:
    def test_mismatch_after_change_is_an_error(self, capsys):
        with mock.patch(
            'main.get_interface_mac',
            side_effect=['11:22:33:44:55:66', '11:22:33:44:55:66'],
        ), mock.patch('main.read_backup', return_value={}), \
           mock.patch('main.write_backup') as mock_write_backup, \
           mock.patch('main.append_history') as mock_append_history, \
           mock.patch('main.change_mac', return_value=True):
            exit_code = run_main([
                '--interface', 'eth0', '--mode', 'manual',
                '--mac', 'aa:bb:cc:dd:ee:ff',
            ])

        assert exit_code == 1
        assert 'double check' in capsys.readouterr().out
        mock_write_backup.assert_not_called()
        mock_append_history.assert_not_called()

    def test_failed_change_mac_returns_a_nonzero_exit_code(self):
        with mock.patch(
            'main.get_interface_mac', return_value='11:22:33:44:55:66'
        ), mock.patch('main.read_backup', return_value={}), \
           mock.patch('main.change_mac', return_value=False):
            exit_code = run_main([
                '--interface', 'eth0', '--mode', 'manual',
                '--mac', 'aa:bb:cc:dd:ee:ff',
            ])
        assert exit_code == 1
