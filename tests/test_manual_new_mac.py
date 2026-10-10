from __future__ import annotations

"""
==============================================================================
Module Name:   test_manual_new_mac.py
Description:   Implementation and logic for test_manual_new_mac.
Author:        Mai Tan Duc <ducmai.network@gmail.com>
Created:       2026-10-10
Version:       1.0.0
License:       MIT
==============================================================================
Usage:         python3 test_manual_new_mac.py [options]
Notes:         Requires Python 3.8+
==============================================================================
"""

from unittest import mock

import main


class TestManualNewMac:
    def test_accepts_a_valid_mac_on_first_try(self) -> None:
        with mock.patch("builtins.input", return_value="01:23:45:67:89:ab"):
            assert main.manual_new_mac() == "01:23:45:67:89:ab"

    def test_strips_surrounding_whitespace(self) -> None:
        with mock.patch("builtins.input", return_value=" 01:23:45:67:89:ab "):
            assert main.manual_new_mac() == "01:23:45:67:89:ab"

    def test_reprompts_on_malformed_input(self, capsys) -> None:
        with mock.patch(
            "builtins.input",
            side_effect=["not a mac", "01:23:45:67:89:ab"],
        ):
            result = main.manual_new_mac()
        assert result == "01:23:45:67:89:ab"
        assert "ERROR" in capsys.readouterr().out
