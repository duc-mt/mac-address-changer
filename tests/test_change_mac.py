"""Tests for main.change_mac().

Regression coverage for the return-code bug found during review: each
subprocess.call()'s exit code used to be discarded entirely, so a
failed step (e.g. bringing the interface down) didn't stop the script
from blindly running the next command anyway.
"""

from __future__ import annotations

from unittest import mock

import main


class TestChangeMac:
    def test_all_steps_succeed(self):
        with mock.patch('main.subprocess.call', return_value=0) as mock_call:
            result = main.change_mac('eth0', 'aa:bb:cc:dd:ee:ff')

        assert result is True
        assert mock_call.call_count == 3
        mock_call.assert_any_call(['ifconfig', 'eth0', 'down'])
        mock_call.assert_any_call(
            ['ifconfig', 'eth0', 'hw', 'ether', 'aa:bb:cc:dd:ee:ff']
        )
        mock_call.assert_any_call(['ifconfig', 'eth0', 'up'])

    def test_stops_after_the_first_failed_step(self, capsys):
        with mock.patch(
            'main.subprocess.call', side_effect=[1]
        ) as mock_call:
            result = main.change_mac('eth0', 'aa:bb:cc:dd:ee:ff')

        assert result is False
        # Only the failed "down" step ran - "hw ether" and "up" must
        # NOT have been attempted on an interface that's already in an
        # unknown state.
        assert mock_call.call_count == 1
        assert 'ERROR' in capsys.readouterr().out

    def test_stops_after_the_second_step_fails(self):
        with mock.patch(
            'main.subprocess.call', side_effect=[0, 1]
        ) as mock_call:
            result = main.change_mac('eth0', 'aa:bb:cc:dd:ee:ff')

        assert result is False
        assert mock_call.call_count == 2
