"""Tests for main.read_backup() and main.write_backup().

The backup file stores "interface,mac" pairs, one per line, replacing
the old format (a bare MAC per line, with no interface name attached -
which made an automatic restore impossible to do safely, since there
was no way to tell which line belonged to which interface).
"""

from __future__ import annotations

import main


class TestReadBackup:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        assert main.read_backup(backup_file) == {}

    def test_reads_back_what_was_written(self, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        backup_file_path = tmp_path / 'real_mac.txt'
        backup_file_path.write_text('eth0,aa:bb:cc:dd:ee:ff\n')

        assert main.read_backup(backup_file) == {
            'eth0': 'aa:bb:cc:dd:ee:ff',
        }

    def test_reads_multiple_interfaces(self, tmp_path):
        backup_file_path = tmp_path / 'real_mac.txt'
        backup_file_path.write_text(
            'eth0,aa:bb:cc:dd:ee:ff\nwlan0,11:22:33:44:55:66\n'
        )

        assert main.read_backup(str(backup_file_path)) == {
            'eth0': 'aa:bb:cc:dd:ee:ff',
            'wlan0': '11:22:33:44:55:66',
        }

    def test_skips_malformed_lines(self, tmp_path):
        backup_file_path = tmp_path / 'real_mac.txt'
        backup_file_path.write_text(
            'eth0,aa:bb:cc:dd:ee:ff\n'
            'this is not a valid line\n'
            '\n'
        )

        assert main.read_backup(str(backup_file_path)) == {
            'eth0': 'aa:bb:cc:dd:ee:ff',
        }

    def test_skips_lines_from_the_old_bare_mac_format(self, tmp_path):
        """Regression test: the old backup format
        (`cat /sys/class/net/*/address > real_mac.txt`) produced one
        bare MAC per line, with no comma and no interface name. Those
        lines must be safely ignored, not misread as garbage data."""
        backup_file_path = tmp_path / 'real_mac.txt'
        backup_file_path.write_text('aa:bb:cc:dd:ee:ff\n11:22:33:44:55:66\n')

        assert main.read_backup(str(backup_file_path)) == {}


class TestWriteBackup:
    def test_writes_a_new_entry(self, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        main.write_backup(backup_file, 'eth0', 'aa:bb:cc:dd:ee:ff')

        assert main.read_backup(backup_file) == {
            'eth0': 'aa:bb:cc:dd:ee:ff',
        }

    def test_adding_a_second_interface_preserves_the_first(self, tmp_path):
        backup_file = str(tmp_path / 'real_mac.txt')
        main.write_backup(backup_file, 'eth0', 'aa:bb:cc:dd:ee:ff')
        main.write_backup(backup_file, 'wlan0', '11:22:33:44:55:66')

        assert main.read_backup(backup_file) == {
            'eth0': 'aa:bb:cc:dd:ee:ff',
            'wlan0': '11:22:33:44:55:66',
        }

    def test_writing_the_same_interface_again_replaces_its_entry(
        self, tmp_path
    ):
        backup_file = str(tmp_path / 'real_mac.txt')
        main.write_backup(backup_file, 'eth0', 'aa:bb:cc:dd:ee:ff')
        main.write_backup(backup_file, 'eth0', '99:99:99:99:99:99')

        assert main.read_backup(backup_file) == {
            'eth0': '99:99:99:99:99:99',
        }
