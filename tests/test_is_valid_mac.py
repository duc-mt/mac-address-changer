from __future__ import annotations

import main


class TestIsValidMac:
    def test_accepts_colon_separated(self):
        assert main.is_valid_mac('01:23:45:67:89:ab') is True

    def test_accepts_hyphen_separated(self):
        assert main.is_valid_mac('01-23-45-67-89-ab') is True

    def test_accepts_uppercase_hex(self):
        assert main.is_valid_mac('01:23:45:67:89:AB') is True

    def test_rejects_too_few_groups(self):
        assert main.is_valid_mac('01:23:45:67:89') is False

    def test_rejects_too_many_groups(self):
        assert main.is_valid_mac('01:23:45:67:89:ab:cd') is False

    def test_rejects_non_hex_characters(self):
        assert main.is_valid_mac('zz:23:45:67:89:ab') is False

    def test_rejects_mixed_separators(self):
        assert main.is_valid_mac('01:23-45:67:89:ab') is False

    def test_rejects_empty_string(self):
        assert main.is_valid_mac('') is False

    def test_rejects_garbage(self):
        assert main.is_valid_mac('not a mac address') is False
