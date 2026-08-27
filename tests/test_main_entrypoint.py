"""Tests for main.run_interactive() (the interactive session) and
main.main() (top-level dispatch between --status/CLI mode/interactive).
"""

from __future__ import annotations

from unittest import mock

import pytest

import main


def run_interactive(inputs):
    with mock.patch('builtins.input', lambda *a: next(iter(inputs))):
        main.run_interactive()


class TestMissingTool:
    def test_missing_ifconfig_and_ip_exits_cleanly_with_a_clear_message(
        self, capsys
    ):
        """Regression test: on a system without ifconfig installed
        (increasingly common - many modern Linux distributions no
        longer ship net-tools by default), this used to crash with an
        unhandled FileNotFoundError instead of a clear message."""
        with mock.patch('main.detect_network_tool', return_value=None), \
             pytest.raises(SystemExit) as exc_info:
            main.run_interactive()

        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert 'neither ip nor ifconfig' in out


class TestInterfaceValidation:
    def test_nonexistent_interface_exits_cleanly_with_available_list(
        self, capsys
    ):
        with mock.patch('main.detect_network_tool', return_value='ip'), \
             mock.patch('builtins.input', return_value='no-such-interface'), \
             mock.patch('main.get_interface_mac', return_value=None), \
             mock.patch('main.list_interfaces', return_value=['eth0', 'lo']), \
             mock.patch('main.change_mac') as mock_change_mac, \
             pytest.raises(SystemExit) as exc_info:
            main.run_interactive()

        assert exc_info.value.code == 1
        mock_change_mac.assert_not_called()
        out = capsys.readouterr().out
        assert 'No such interface' in out
        assert 'eth0, lo' in out

    def test_interface_name_input_is_trimmed(self):
        inputs = iter([' eth0 ', '2'])
        with mock.patch('main.detect_network_tool', return_value='ip'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.get_interface_mac', return_value='11:22:33:44:55:66'
             ) as mock_get_mac, \
             mock.patch('main.read_backup', return_value={}), \
             mock.patch('main.write_backup'), \
             mock.patch('main.append_history'), \
             mock.patch(
                 'main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'
             ), \
             mock.patch('main.change_mac', return_value=True):
            main.run_interactive()

        mock_get_mac.assert_any_call('eth0')  # not ' eth0 '


class TestAutomaticBackup:
    def test_first_time_seeing_an_interface_backs_it_up(self, capsys):
        inputs = iter(['eth0', '2'])
        with mock.patch('main.detect_network_tool', return_value='ip'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.get_interface_mac', return_value='11:22:33:44:55:66'
             ), \
             mock.patch('main.read_backup', return_value={}), \
             mock.patch('main.write_backup') as mock_write_backup, \
             mock.patch('main.append_history'), \
             mock.patch(
                 'main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'
             ), \
             mock.patch('main.change_mac', return_value=True):
            main.run_interactive()

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
        with mock.patch('main.detect_network_tool', return_value='ip'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.get_interface_mac', return_value='aa:aa:aa:aa:aa:aa'
             ), \
             mock.patch(
                 'main.read_backup',
                 return_value={'eth0': '11:22:33:44:55:66'},
             ), \
             mock.patch('main.write_backup') as mock_write_backup, \
             mock.patch('main.append_history'), \
             mock.patch(
                 'main.random_new_mac', return_value='bb:bb:bb:bb:bb:bb'
             ), \
             mock.patch('main.change_mac', return_value=True):
            main.run_interactive()

        mock_write_backup.assert_not_called()
        assert 'Backed up' not in capsys.readouterr().out


class TestChangeVerification:
    def test_successful_change_is_verified_against_the_new_mac(self, capsys):
        """Regression test: previously "success" meant only "ifconfig's
        exit code was 0" - the script never actually confirmed the
        interface's MAC had changed to the intended value."""
        inputs = iter(['eth0', '2'])
        with mock.patch('main.detect_network_tool', return_value='ip'), \
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
             mock.patch('main.append_history'), \
             mock.patch('main.change_mac', return_value=True):
            main.run_interactive()

        out = capsys.readouterr().out
        assert 'from 11:22:33:44:55:66 to aa:bb:cc:dd:ee:ff' in out
        assert 'Success' in out

    def test_mismatch_after_change_is_reported_not_silently_trusted(
        self, capsys
    ):
        inputs = iter(['eth0', '2'])
        with mock.patch('main.detect_network_tool', return_value='ip'), \
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
             mock.patch('main.append_history') as mock_append_history, \
             mock.patch('main.change_mac', return_value=True):
            main.run_interactive()

        out = capsys.readouterr().out
        assert 'double check' in out
        # A mismatch means the change can't be trusted - it must not
        # be recorded as a successful, undoable change.
        mock_append_history.assert_not_called()

    def test_failed_change_mac_prints_no_success_message(self, capsys):
        inputs = iter(['eth0', '2'])
        with mock.patch('main.detect_network_tool', return_value='ip'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'
             ), \
             mock.patch(
                 'main.get_interface_mac', return_value='11:22:33:44:55:66'
             ), \
             mock.patch('main.read_backup', return_value={}), \
             mock.patch('main.write_backup'), \
             mock.patch('main.append_history') as mock_append_history, \
             mock.patch('main.change_mac', return_value=False):
            main.run_interactive()

        out = capsys.readouterr().out
        assert 'Success' not in out
        mock_append_history.assert_not_called()


class TestHistoryRecording:
    def test_manual_random_and_restore_changes_are_recorded_to_history(
        self, capsys
    ):
        inputs = iter(['eth0', '2'])
        with mock.patch('main.detect_network_tool', return_value='ip'), \
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
             mock.patch('main.append_history') as mock_append_history, \
             mock.patch('main.pop_last_history') as mock_pop_history, \
             mock.patch('main.change_mac', return_value=True):
            main.run_interactive()

        mock_append_history.assert_called_once_with(
            main.HISTORY_FILE, 'eth0', '11:22:33:44:55:66'
        )
        mock_pop_history.assert_not_called()

    def test_undo_consumes_a_history_entry_instead_of_recording_a_new_one(
        self, capsys
    ):
        # No backup is mocked (read_backup returns {}), so - with the
        # dynamic menu numbering - undo is offered as option "3" here,
        # not "4" (that would only be the case if restore were also
        # available). See test_user_choice.py's
        # test_menu_numbering_has_no_gap_when_only_undo_is_available
        # for the regression this numbering itself guards against.
        inputs = iter(['eth0', '3'])
        with mock.patch('main.detect_network_tool', return_value='ip'), \
             mock.patch('builtins.input', lambda *a: next(inputs)), \
             mock.patch(
                 'main.get_interface_mac',
                 side_effect=['bb:bb:bb:bb:bb:bb', 'aa:aa:aa:aa:aa:aa'],
             ), \
             mock.patch('main.read_backup', return_value={}), \
             mock.patch('main.write_backup'), \
             mock.patch(
                 'main.read_history',
                 return_value={'eth0': ['11:22:33:44:55:66', 'aa:aa:aa:aa:aa:aa']},
             ), \
             mock.patch('main.append_history') as mock_append_history, \
             mock.patch('main.pop_last_history') as mock_pop_history, \
             mock.patch('main.change_mac', return_value=True):
            main.run_interactive()

        mock_pop_history.assert_called_once_with(main.HISTORY_FILE, 'eth0')
        mock_append_history.assert_not_called()


class TestMainDispatch:
    def test_status_flag_prints_status_and_does_not_run_interactive(self):
        with mock.patch('sys.argv', ['main.py', '--status']), \
             mock.patch('main.detect_network_tool', return_value='ip'), \
             mock.patch('main.print_status') as mock_print_status, \
             mock.patch('main.run_interactive') as mock_run_interactive:
            exit_code = main.main()

        assert exit_code == 0
        mock_print_status.assert_called_once()
        mock_run_interactive.assert_not_called()

    def test_no_arguments_runs_the_interactive_menu(self):
        with mock.patch('sys.argv', ['main.py']), \
             mock.patch('main.detect_network_tool', return_value='ip'), \
             mock.patch('main.run_interactive') as mock_run_interactive:
            exit_code = main.main()

        assert exit_code == 0
        mock_run_interactive.assert_called_once()

    def test_missing_tool_exits_before_dispatching_anywhere(self, capsys):
        with mock.patch('sys.argv', ['main.py']), \
             mock.patch('main.detect_network_tool', return_value=None), \
             mock.patch('main.run_interactive') as mock_run_interactive:
            exit_code = main.main()

        assert exit_code == 1
        mock_run_interactive.assert_not_called()
        assert 'neither ip nor ifconfig' in capsys.readouterr().out

    def test_interface_without_mode_is_an_error(self):
        with mock.patch('sys.argv', ['main.py', '--interface', 'eth0']), \
             mock.patch('main.detect_network_tool', return_value='ip'), \
             pytest.raises(SystemExit) as exc_info:
            main.main()
        assert exc_info.value.code == 2

    def test_mode_without_interface_is_an_error(self):
        with mock.patch('sys.argv', ['main.py', '--mode', 'random']), \
             mock.patch('main.detect_network_tool', return_value='ip'), \
             pytest.raises(SystemExit) as exc_info:
            main.main()
        assert exc_info.value.code == 2
