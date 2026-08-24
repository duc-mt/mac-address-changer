"""Tests for main.get_interface_mac() and main.list_interfaces().

Both read from SYSFS_NET_PATH rather than the hardcoded /sys/class/net,
so tests point it at a throwaway directory instead of touching the
real sysfs.
"""

from __future__ import annotations

import main


def make_fake_sysfs(tmp_path, interfaces):
    """Build a directory shaped like /sys/class/net, with one
    subdirectory + address file per {name: mac} pair in `interfaces`."""
    for name, mac in interfaces.items():
        iface_dir = tmp_path / name
        iface_dir.mkdir()
        (iface_dir / "address").write_text(mac + "\n")
    return tmp_path


class TestGetInterfaceMac:
    def test_returns_the_mac_for_an_existing_interface(
        self, tmp_path, monkeypatch
    ):
        make_fake_sysfs(tmp_path, {"eth0": "aa:bb:cc:dd:ee:ff"})
        monkeypatch.setattr(main, "SYSFS_NET_PATH", str(tmp_path))

        assert main.get_interface_mac("eth0") == "aa:bb:cc:dd:ee:ff"

    def test_strips_trailing_whitespace(self, tmp_path, monkeypatch):
        (tmp_path / "eth0").mkdir()
        (tmp_path / "eth0" / "address").write_text("aa:bb:cc:dd:ee:ff\n\n")
        monkeypatch.setattr(main, "SYSFS_NET_PATH", str(tmp_path))

        assert main.get_interface_mac("eth0") == "aa:bb:cc:dd:ee:ff"

    def test_returns_none_for_a_nonexistent_interface(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(main, "SYSFS_NET_PATH", str(tmp_path))

        assert main.get_interface_mac("wlan9") is None

    def test_returns_none_when_sysfs_path_itself_is_missing(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            main, "SYSFS_NET_PATH", str(tmp_path / "does-not-exist")
        )

        assert main.get_interface_mac("eth0") is None


class TestListInterfaces:
    def test_lists_every_interface_sorted(self, tmp_path, monkeypatch):
        make_fake_sysfs(
            tmp_path,
            {"wlan0": "11:22:33:44:55:66", "eth0": "aa:bb:cc:dd:ee:ff"},
        )
        monkeypatch.setattr(main, "SYSFS_NET_PATH", str(tmp_path))

        assert main.list_interfaces() == ["eth0", "wlan0"]

    def test_empty_when_sysfs_path_is_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            main, "SYSFS_NET_PATH", str(tmp_path / "does-not-exist")
        )

        assert main.list_interfaces() == []
