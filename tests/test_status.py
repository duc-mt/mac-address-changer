from __future__ import annotations

from unittest import mock

import main


def make_fake_sysfs(tmp_path, interfaces):
    for name, mac in interfaces.items():
        iface_dir = tmp_path / name
        iface_dir.mkdir()
        (iface_dir / 'address').write_text(mac + '\n')
    return tmp_path


class TestPrintStatus:
    def test_no_interfaces_prints_a_clear_message(self, capsys):
        with mock.patch('main.list_interfaces', return_value=[]):
            main.print_status()

        assert 'No network interfaces found' in capsys.readouterr().out

    def test_lists_every_interface_with_its_current_mac(
        self, capsys, tmp_path
    ):
        make_fake_sysfs(tmp_path, {'eth0': '11:22:33:44:55:66'})

        with mock.patch('main.SYSFS_NET_PATH', str(tmp_path)), \
             mock.patch('main.BACKUP_FILE', str(tmp_path / 'real_mac.txt')), \
             mock.patch('main.HISTORY_FILE', str(tmp_path / 'mac_history.txt')):
            main.print_status()

        out = capsys.readouterr().out
        assert 'eth0' in out
        assert '11:22:33:44:55:66' in out

    def test_shows_a_dash_when_no_backup_exists(self, capsys, tmp_path):
        make_fake_sysfs(tmp_path, {'eth0': '11:22:33:44:55:66'})

        with mock.patch('main.SYSFS_NET_PATH', str(tmp_path)), \
             mock.patch('main.BACKUP_FILE', str(tmp_path / 'real_mac.txt')), \
             mock.patch('main.HISTORY_FILE', str(tmp_path / 'mac_history.txt')):
            main.print_status()

        lines = capsys.readouterr().out.splitlines()
        eth0_line = next(line for line in lines if line.startswith('eth0'))
        assert '-' in eth0_line

    def test_shows_the_backed_up_original_when_one_exists(
        self, capsys, tmp_path
    ):
        make_fake_sysfs(tmp_path, {'eth0': 'aa:aa:aa:aa:aa:aa'})
        backup_file = str(tmp_path / 'real_mac.txt')
        main.write_backup(backup_file, 'eth0', '11:22:33:44:55:66')

        with mock.patch('main.SYSFS_NET_PATH', str(tmp_path)), \
             mock.patch('main.BACKUP_FILE', backup_file), \
             mock.patch('main.HISTORY_FILE', str(tmp_path / 'mac_history.txt')):
            main.print_status()

        out = capsys.readouterr().out
        assert '11:22:33:44:55:66' in out

    def test_shows_the_number_of_undo_steps_available(self, capsys, tmp_path):
        make_fake_sysfs(tmp_path, {'eth0': 'aa:aa:aa:aa:aa:aa'})
        history_file = str(tmp_path / 'mac_history.txt')
        main.append_history(history_file, 'eth0', '11:22:33:44:55:66')
        main.append_history(history_file, 'eth0', 'bb:bb:bb:bb:bb:bb')

        with mock.patch('main.SYSFS_NET_PATH', str(tmp_path)), \
             mock.patch('main.BACKUP_FILE', str(tmp_path / 'real_mac.txt')), \
             mock.patch('main.HISTORY_FILE', history_file):
            main.print_status()

        lines = capsys.readouterr().out.splitlines()
        eth0_line = next(line for line in lines if line.startswith('eth0'))
        assert eth0_line.rstrip().endswith('2')
