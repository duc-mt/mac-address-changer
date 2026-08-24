from __future__ import annotations

from unittest import mock

import main


class TestManualNewMac:
    def test_accepts_a_valid_mac_on_first_try(self):
        with mock.patch('builtins.input', return_value='01:23:45:67:89:ab'):
            assert main.manual_new_mac() == '01:23:45:67:89:ab'

    def test_strips_surrounding_whitespace(self):
        with mock.patch('builtins.input', return_value=' 01:23:45:67:89:ab '):
            assert main.manual_new_mac() == '01:23:45:67:89:ab'

    def test_reprompts_on_malformed_input(self, capsys):
        with mock.patch(
            'builtins.input',
            side_effect=['not a mac', '01:23:45:67:89:ab'],
        ):
            result = main.manual_new_mac()
        assert result == '01:23:45:67:89:ab'
        assert 'ERROR' in capsys.readouterr().out
