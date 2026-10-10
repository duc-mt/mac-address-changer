"""
==============================================================================
Module Name:   test_random_new_mac.py
Description:   Source module test_random_new_mac.py.
Author:        Mai Tan Duc <ducmai.network@gmail.com>
Created:       2026-10-10
Version:       1.0.0
License:       MIT
==============================================================================
Usage:         python3 test_random_new_mac.py [options]
Notes:         Requires Python 3.8+
==============================================================================
"""

from __future__ import annotations

import main


class TestMakeLocallyAdministered:
    def test_clears_the_multicast_bit(self) -> None:
        for byte in range(256):
            result = main.make_locally_administered(byte)
            assert result & 0b00000001 == 0

    def test_sets_the_locally_administered_bit(self) -> None:
        for byte in range(256):
            result = main.make_locally_administered(byte)
            assert result & 0b00000010 != 0

    def test_only_touches_the_bottom_two_bits(self) -> None:
        # The rest of the byte should be a completely free random
        # value - this isn't trying to hide which bytes are "special".
        assert main.make_locally_administered(0b11111100) == 0b11111110
        assert main.make_locally_administered(0b00000000) == 0b00000010


class TestRandomNewMac:
    def test_every_generated_address_is_well_formed(self) -> None:
        for _ in range(200):
            assert main.is_valid_mac(main.random_new_mac())

    def test_every_generated_address_is_a_valid_unicast_mac(self) -> None:
        """Regression test for the ~50% failure rate confirmed during
        review: the first octet's multicast bit must never be set."""
        for _ in range(200):
            mac = main.random_new_mac()
            first_octet = int(mac.split(":")[0], 16)
            assert first_octet & 0x01 == 0

    def test_addresses_are_not_all_identical(self) -> None:
        # Sanity check that this is actually random, not a constant.
        addresses = {main.random_new_mac() for _ in range(50)}
        assert len(addresses) > 1
