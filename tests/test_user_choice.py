from __future__ import annotations

from unittest import mock

import main


class TestUserChoice:
    def test_choice_1_calls_manual_new_mac(self, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        with mock.patch('builtins.input', return_value='1'), \
             mock.patch('main.manual_new_mac', return_value='aa:bb:cc:dd:ee:ff'):
            result = main.user_choice('eth0', backup_file, history_file)
        assert result == ('aa:bb:cc:dd:ee:ff', 'manual')

    def test_choice_2_calls_random_new_mac(self, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        with mock.patch('builtins.input', return_value='2'), \
             mock.patch('main.random_new_mac', return_value='11:22:33:44:55:66'):
            result = main.user_choice('eth0', backup_file, history_file)
        assert result == ('11:22:33:44:55:66', 'random')

    def test_out_of_range_number_reprompts(self, capsys, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        with mock.patch('builtins.input', side_effect=['5', '2']), \
             mock.patch('main.random_new_mac', return_value='11:22:33:44:55:66'):
            result = main.user_choice('eth0', backup_file, history_file)
        assert result == ('11:22:33:44:55:66', 'random')
        assert 'WRONG INPUT' in capsys.readouterr().out

    def test_non_integer_input_does_not_crash(self, capsys, tmp_path):
        """Regression test: int(input(...)) used to be called directly,
        raising an unhandled ValueError - crashing the whole program -
        the instant anyone typed anything that wasn't a number."""
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        with mock.patch(
            'builtins.input', side_effect=['not a number', '', '2']
        ), mock.patch('main.random_new_mac', return_value='11:22:33:44:55:66'):
            result = main.user_choice('eth0', backup_file, history_file)
        assert result == ('11:22:33:44:55:66', 'random')
        assert 'WRONG INPUT' in capsys.readouterr().out


class TestUserChoiceRestoreOption:
    def test_restore_option_offered_when_a_backup_exists(self, capsys, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        main.write_backup(backup_file, 'eth0', '11:22:33:44:55:66')

        with mock.patch('builtins.input', return_value='3'):
            result = main.user_choice('eth0', backup_file, history_file)

        assert result == ('11:22:33:44:55:66', 'restore')
        assert 'restore original' in capsys.readouterr().out

    def test_restore_option_not_offered_without_a_backup(self, capsys, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')  # never written to
        history_file = str(tmp_path / 'mac_history.txt')

        with mock.patch('builtins.input', return_value='2'), \
             mock.patch('main.random_new_mac', return_value='11:22:33:44:55:66'):
            main.user_choice('eth0', backup_file, history_file)

        assert 'restore original' not in capsys.readouterr().out

    def test_restore_option_is_specific_to_the_given_interface(
        self, capsys, tmp_path
    ):
        """A backup existing for a *different* interface must not
        offer "restore" for this one."""
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        main.write_backup(backup_file, 'wlan0', '11:22:33:44:55:66')

        with mock.patch('builtins.input', return_value='2'), \
             mock.patch('main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'):
            main.user_choice('eth0', backup_file, history_file)

        assert 'restore original' not in capsys.readouterr().out

    def test_choosing_a_number_beyond_the_offered_menu_reprompts(
        self, capsys, tmp_path
    ):
        # No backup or history exists, so only 1-2 are valid; 3 must
        # be rejected exactly like any other out-of-range choice.
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        with mock.patch('builtins.input', side_effect=['3', '2']), \
             mock.patch('main.random_new_mac', return_value='11:22:33:44:55:66'):
            result = main.user_choice('eth0', backup_file, history_file)
        assert result == ('11:22:33:44:55:66', 'random')
        assert 'WRONG INPUT' in capsys.readouterr().out


class TestUserChoiceUndoOption:
    def test_undo_option_offered_when_history_exists(self, capsys, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        main.append_history(history_file, 'eth0', '11:22:33:44:55:66')
        main.append_history(history_file, 'eth0', 'aa:aa:aa:aa:aa:aa')

        # No backup exists, so undo is the *third* offered option
        # here (there's no gap at "3" - see the regression test
        # below for why that matters).
        with mock.patch('builtins.input', return_value='3'):
            result = main.user_choice('eth0', backup_file, history_file)

        # The most recently appended entry is offered - not the
        # oldest.
        assert result == ('aa:aa:aa:aa:aa:aa', 'undo')
        assert 'undo last change' in capsys.readouterr().out

    def test_menu_numbering_has_no_gap_when_only_undo_is_available(
        self, capsys, tmp_path
    ):
        """Regression test: undo used to always be hardcoded as
        option "4", even when restore (option "3") wasn't offered -
        leaving a gap that no valid choice mapped to. Scripted/typoed
        input of the missing number retried forever instead of being
        rejected once, since the retry loop only stops once a valid
        choice is entered."""
        backup_file = str(tmp_path / 'real_mac.txt')  # no backup
        history_file = str(tmp_path / 'mac_history.txt')
        main.append_history(history_file, 'eth0', '11:22:33:44:55:66')

        with mock.patch('builtins.input', return_value='3'):
            result = main.user_choice('eth0', backup_file, history_file)

        assert result == ('11:22:33:44:55:66', 'undo')

    def test_undo_option_not_offered_without_history(self, capsys, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')  # never written to

        with mock.patch('builtins.input', return_value='2'), \
             mock.patch('main.random_new_mac', return_value='11:22:33:44:55:66'):
            main.user_choice('eth0', backup_file, history_file)

        assert 'undo last change' not in capsys.readouterr().out

    def test_undo_option_is_specific_to_the_given_interface(
        self, capsys, tmp_path
    ):
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        main.append_history(history_file, 'wlan0', '11:22:33:44:55:66')

        with mock.patch('builtins.input', return_value='2'), \
             mock.patch('main.random_new_mac', return_value='aa:bb:cc:dd:ee:ff'):
            main.user_choice('eth0', backup_file, history_file)

        assert 'undo last change' not in capsys.readouterr().out

    def test_both_restore_and_undo_can_be_offered_together(self, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        history_file = str(tmp_path / 'mac_history.txt')
        main.write_backup(backup_file, 'eth0', '11:22:33:44:55:66')
        main.append_history(history_file, 'eth0', 'aa:aa:aa:aa:aa:aa')

        with mock.patch('builtins.input', return_value='4'):
            result = main.user_choice('eth0', backup_file, history_file)

        assert result == ('aa:aa:aa:aa:aa:aa', 'undo')
