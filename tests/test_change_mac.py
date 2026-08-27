"""Tests for main.change_mac(), main.detect_network_tool(), and
main.build_change_commands().

Regression coverage for two bugs found during review:

1. Each subprocess.call()'s exit code used to be discarded entirely,
   so a failed step didn't stop the script from blindly running the
   next command anyway.
2. Only ifconfig (from net-tools) was ever tried, which many modern
   Linux distributions no longer install by default. `ip` (from
   iproute2, nearly universal) is now tried first, with ifconfig as a
   fallback.
"""

from __future__ import annotations

from unittest import mock

import main


class TestDetectNetworkTool:
    def test_prefers_ip_when_both_are_available(self):
        with mock.patch(
            'shutil.which', side_effect=lambda cmd: f'/usr/sbin/{cmd}'
        ):
            assert main.detect_network_tool() == 'ip'

    def test_falls_back_to_ifconfig_when_ip_is_missing(self):
        with mock.patch(
            'shutil.which',
            side_effect=lambda cmd: '/sbin/ifconfig' if cmd == 'ifconfig' else None,
        ):
            assert main.detect_network_tool() == 'ifconfig'

    def test_returns_none_when_neither_is_available(self):
        with mock.patch('shutil.which', return_value=None):
            assert main.detect_network_tool() is None


class TestBuildChangeCommands:
    def test_ip_commands(self):
        commands = main.build_change_commands(
            'ip', 'eth0', 'aa:bb:cc:dd:ee:ff'
        )
        assert commands == [
            ['ip', 'link', 'set', 'dev', 'eth0', 'down'],
            ['ip', 'link', 'set', 'dev', 'eth0', 'address', 'aa:bb:cc:dd:ee:ff'],
            ['ip', 'link', 'set', 'dev', 'eth0', 'up'],
        ]

    def test_ifconfig_commands(self):
        commands = main.build_change_commands(
            'ifconfig', 'eth0', 'aa:bb:cc:dd:ee:ff'
        )
        assert commands == [
            ['ifconfig', 'eth0', 'down'],
            ['ifconfig', 'eth0', 'hw', 'ether', 'aa:bb:cc:dd:ee:ff'],
            ['ifconfig', 'eth0', 'up'],
        ]


class TestChangeMac:
    def test_all_steps_succeed_with_ip(self):
        with mock.patch('main.subprocess.call', return_value=0) as mock_call:
            result = main.change_mac('eth0', 'aa:bb:cc:dd:ee:ff', tool='ip')

        assert result is True
        assert mock_call.call_count == 3
        mock_call.assert_any_call(['ip', 'link', 'set', 'dev', 'eth0', 'down'])
        mock_call.assert_any_call(
            ['ip', 'link', 'set', 'dev', 'eth0', 'address', 'aa:bb:cc:dd:ee:ff']
        )
        mock_call.assert_any_call(['ip', 'link', 'set', 'dev', 'eth0', 'up'])

    def test_all_steps_succeed_with_ifconfig(self):
        with mock.patch('main.subprocess.call', return_value=0) as mock_call:
            result = main.change_mac(
                'eth0', 'aa:bb:cc:dd:ee:ff', tool='ifconfig'
            )

        assert result is True
        mock_call.assert_any_call(
            ['ifconfig', 'eth0', 'hw', 'ether', 'aa:bb:cc:dd:ee:ff']
        )

    def test_auto_detects_the_tool_when_none_given(self):
        with mock.patch('main.detect_network_tool', return_value='ip'), \
             mock.patch('main.subprocess.call', return_value=0) as mock_call:
            main.change_mac('eth0', 'aa:bb:cc:dd:ee:ff')

        assert mock_call.call_args_list[0][0][0][0] == 'ip'

    def test_stops_after_the_first_failed_step(self, capsys):
        with mock.patch(
            'main.subprocess.call', side_effect=[1]
        ) as mock_call:
            result = main.change_mac('eth0', 'aa:bb:cc:dd:ee:ff', tool='ip')

        assert result is False
        # Only the failed "down" step ran - "address" and "up" must
        # NOT have been attempted on an interface that's already in an
        # unknown state.
        assert mock_call.call_count == 1
        assert 'ERROR' in capsys.readouterr().out

    def test_stops_after_the_second_step_fails(self):
        with mock.patch(
            'main.subprocess.call', side_effect=[0, 1]
        ) as mock_call:
            result = main.change_mac('eth0', 'aa:bb:cc:dd:ee:ff', tool='ip')

        assert result is False
        assert mock_call.call_count == 2

    def test_neither_tool_available_fails_cleanly(self, capsys):
        with mock.patch('main.detect_network_tool', return_value=None), \
             mock.patch('main.subprocess.call') as mock_call:
            result = main.change_mac('eth0', 'aa:bb:cc:dd:ee:ff')

        assert result is False
        mock_call.assert_not_called()
        assert 'neither ip nor ifconfig' in capsys.readouterr().out
