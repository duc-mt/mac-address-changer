"""Tests for main.read_history(), main.append_history(), and
main.pop_last_history() - the change-history mechanism behind "undo
last change", distinct from the backup file (which only ever
remembers the true original).
"""

from __future__ import annotations

import main


class TestReadHistory:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        path = str(tmp_path / 'mac_history.txt')
        assert main.read_history(path) == {}

    def test_reads_multiple_entries_for_one_interface_in_order(self, tmp_path):
        path = tmp_path / 'mac_history.txt'
        path.write_text('eth0,11:22:33:44:55:66\neth0,aa:aa:aa:aa:aa:aa\n')

        assert main.read_history(str(path)) == {
            'eth0': ['11:22:33:44:55:66', 'aa:aa:aa:aa:aa:aa'],
        }

    def test_reads_entries_for_multiple_interfaces_separately(self, tmp_path):
        path = tmp_path / 'mac_history.txt'
        path.write_text('eth0,11:22:33:44:55:66\nwlan0,aa:aa:aa:aa:aa:aa\n')

        assert main.read_history(str(path)) == {
            'eth0': ['11:22:33:44:55:66'],
            'wlan0': ['aa:aa:aa:aa:aa:aa'],
        }

    def test_skips_malformed_lines(self, tmp_path):
        path = tmp_path / 'mac_history.txt'
        path.write_text('eth0,11:22:33:44:55:66\nnot a valid line\n')

        assert main.read_history(str(path)) == {
            'eth0': ['11:22:33:44:55:66'],
        }


class TestAppendHistory:
    def test_appends_a_new_entry(self, tmp_path):
        path = str(tmp_path / 'mac_history.txt')
        main.append_history(path, 'eth0', '11:22:33:44:55:66')

        assert main.read_history(path) == {'eth0': ['11:22:33:44:55:66']}

    def test_appends_are_kept_in_order(self, tmp_path):
        path = str(tmp_path / 'mac_history.txt')
        main.append_history(path, 'eth0', '11:22:33:44:55:66')
        main.append_history(path, 'eth0', 'aa:aa:aa:aa:aa:aa')

        assert main.read_history(path) == {
            'eth0': ['11:22:33:44:55:66', 'aa:aa:aa:aa:aa:aa'],
        }

    def test_different_interfaces_do_not_interfere(self, tmp_path):
        path = str(tmp_path / 'mac_history.txt')
        main.append_history(path, 'eth0', '11:22:33:44:55:66')
        main.append_history(path, 'wlan0', 'aa:aa:aa:aa:aa:aa')

        history = main.read_history(path)
        assert history['eth0'] == ['11:22:33:44:55:66']
        assert history['wlan0'] == ['aa:aa:aa:aa:aa:aa']

    def test_trims_to_max_entries_keeping_the_most_recent(self, tmp_path):
        path = str(tmp_path / 'mac_history.txt')
        for i in range(8):
            main.append_history(
                path, 'eth0', f'aa:aa:aa:aa:aa:0{i}', max_entries=5
            )

        entries = main.read_history(path)['eth0']
        assert len(entries) == 5
        assert entries[0] == 'aa:aa:aa:aa:aa:03'  # oldest kept
        assert entries[-1] == 'aa:aa:aa:aa:aa:07'  # most recent


class TestPopLastHistory:
    def test_returns_and_removes_the_most_recent_entry(self, tmp_path):
        path = str(tmp_path / 'mac_history.txt')
        main.append_history(path, 'eth0', '11:22:33:44:55:66')
        main.append_history(path, 'eth0', 'aa:aa:aa:aa:aa:aa')

        popped = main.pop_last_history(path, 'eth0')

        assert popped == 'aa:aa:aa:aa:aa:aa'
        assert main.read_history(path) == {'eth0': ['11:22:33:44:55:66']}

    def test_removes_the_interface_entirely_once_empty(self, tmp_path):
        path = str(tmp_path / 'mac_history.txt')
        main.append_history(path, 'eth0', '11:22:33:44:55:66')

        main.pop_last_history(path, 'eth0')

        assert main.read_history(path) == {}

    def test_returns_none_when_there_is_no_history(self, tmp_path):
        path = str(tmp_path / 'mac_history.txt')
        assert main.pop_last_history(path, 'eth0') is None

    def test_does_not_affect_other_interfaces(self, tmp_path):
        path = str(tmp_path / 'mac_history.txt')
        main.append_history(path, 'eth0', '11:22:33:44:55:66')
        main.append_history(path, 'wlan0', 'aa:aa:aa:aa:aa:aa')

        main.pop_last_history(path, 'eth0')

        assert main.read_history(path) == {'wlan0': ['aa:aa:aa:aa:aa:aa']}
