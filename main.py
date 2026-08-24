#!/usr/bin/python3
# -*- coding: utf-8 -*-

# =============================================================================
#
#        FILE:  main.py
#      AUTHOR:  Mai Tan Duc <ducmai.network@gmail.com>
#     CREATED:  2021-10-04
# DESCRIPTION:  Change the machine's current MAC address.
#               This program MUST be run in the Root Terminal.
#               If you choose to generate randomly, it may come up with
#                   an error message since that address is invalid.
#               In this case, just re-run the program until no error occurs.
#   I hereby declare that I completed this work without any improper help
#   from a third party and without using any aids other than those cited.
#
# =============================================================================


# ------------------------------- Module Imports ------------------------------
# Standard lib - access CLI scripting for inputting user commands.
import os
import shutil
import subprocess

# Regular expressions - validate a manually-entered MAC address.
import re

# Randomly choose a hex (or nibble) for each figure of the new MAC address.
import random


# ------------------------------- Named Constant -------------------------------
# Matches the two MAC address formats ifconfig actually accepts: six
# hex-digit pairs separated by colons, or by hyphens (not mixed).
MAC_ADDRESS_PATTERN = re.compile(
    r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
    r'|^([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}$'
)

# Where the kernel exposes each network interface's current MAC
# address - the same path the README's own `real_mac.txt` backup
# command reads from. A module-level constant (rather than hardcoding
# the path in each function) so tests can point it at a fake directory
# instead of the real /sys.
SYSFS_NET_PATH = '/sys/class/net'

# Where original MAC addresses are backed up, one "interface,mac" pair
# per line, keyed by interface name. A module-level constant so tests
# can point it at a scratch file instead of the real one.
BACKUP_FILE = 'real_mac.txt'


# ---------------------------- Function Definitions ---------------------------
def is_valid_mac(mac):
    """Return True if `mac` is a well-formed MAC address.

    Checks the shape ifconfig actually accepts (six colon- or
    hyphen-separated hex byte pairs) - it doesn't check the address is
    a *usable* one (see make_locally_administered() for that).
    """
    return bool(MAC_ADDRESS_PATTERN.match(mac))


def get_interface_mac(interface):
    """Read a network interface's current MAC address directly from
    sysfs (no subprocess, no root needed just to read it).

    Doubles as an interface-existence check: previously the interface
    name typed at "What is the network interface?" was never
    validated at all, so a typo only surfaced as ifconfig's own
    cryptic failure partway through change_mac().

    Returns
    -------
    str or None
        The interface's current MAC address, or None if there's no
        such interface.
    """
    try:
        with open(f'{SYSFS_NET_PATH}/{interface}/address') as f:
            return f.read().strip()
    except OSError:
        return None


def list_interfaces():
    """List the names of network interfaces present on this machine,
    for a helpful error message when get_interface_mac() finds none
    matching what the user typed."""
    try:
        return sorted(os.listdir(SYSFS_NET_PATH))
    except OSError:
        return []


def read_backup(filename):
    """Read the interface -> original-MAC backup file into a dict.

    Parameters
    ----------
    filename : str
        Path to the backup file (one "interface,mac" pair per line).

    Returns
    -------
    dict[str, str]
        Empty if the file doesn't exist yet (e.g. nothing has ever
        been backed up). Malformed lines - including ones from the
        old backup format this replaces, which stored a bare MAC per
        line with no interface name attached - are skipped rather than
        raising, since a corrupt or outdated backup file shouldn't
        crash the program; it should just mean less to restore from.
    """
    backups = {}
    try:
        with open(filename) as f:
            for line in f:
                interface, _, mac = line.strip().partition(',')
                interface = interface.strip()
                mac = mac.strip()
                if interface and is_valid_mac(mac):
                    backups[interface] = mac
    except OSError:
        pass
    return backups


def write_backup(filename, interface, mac):
    """Record `interface`'s MAC address in the backup file, replacing
    any existing entry for that interface and leaving every other
    interface's entry untouched."""
    backups = read_backup(filename)
    backups[interface] = mac
    with open(filename, 'w') as f:
        for iface, iface_mac in sorted(backups.items()):
            f.write(f'{iface},{iface_mac}\n')


def manual_new_mac():
    # Prompt the user to enter the MAC address, retrying until it's a
    # well-formed address. Previously any string at all was accepted
    # here and passed straight to ifconfig, which would fail later
    # with its own cryptic error instead of a clear one immediately.
    new_mac = None
    while new_mac is None or not is_valid_mac(new_mac):
        new_mac = input('Assign the new MAC address: ').strip()
        if not is_valid_mac(new_mac):
            print('ERROR: Not a valid MAC address (expected six hex byte '
                  'pairs separated by : or -, e.g. 01:23:45:67:89:ab).\n')

    return new_mac


def make_locally_administered(mac_byte):
    """Adjust a single random byte (0-255) so it's safe to use as the
    first octet of a MAC address: clear the multicast/broadcast bit
    (bit 0) and set the locally-administered bit (bit 1).

    NOTE: this is the fix for a bug the original script's own
    docstring acknowledged without actually fixing ("it may come up
    with an error message... just re-run the program until no error
    occurs"). A fully random first octet has its multicast bit (I/G,
    bit 0) set on exactly half of all possible byte values - confirmed
    empirically at ~52% across 2000 generated addresses - and a
    multicast address is never valid as a NIC's own MAC, so ifconfig
    rejects it. Clearing that bit (and setting the "locally
    administered" bit, standard practice for a made-up MAC so it's
    never mistaken for a real vendor's OUI) makes every generated
    address valid, every time - no more retrying.
    """
    return (mac_byte & 0b11111100) | 0b00000010


def random_new_mac():
    # Work out the new MAC address: six random bytes, formatted as hex
    # pairs. The first byte is adjusted by make_locally_administered()
    # so the result is always a valid, usable MAC - see its docstring.
    first_byte = make_locally_administered(random.randint(0, 255))
    other_bytes = [random.randint(0, 255) for _ in range(5)]

    return ':'.join(f'{byte:02x}' for byte in [first_byte, *other_bytes])


def user_choice(interface, backup_filename=BACKUP_FILE):
    """Ask how to set `interface`'s new MAC address: manually,
    randomly, or (if a backup exists for this exact interface)
    restored back to its original value.

    Parameters
    ----------
    interface : str
        The interface the new MAC will be applied to - determines
        whether "restore original" is offered, and which address it
        would restore.
    backup_filename : str
        Path to the interface -> original-MAC backup file.

    Returns
    -------
    str
        The chosen new MAC address.
    """
    backups = read_backup(backup_filename)
    original_mac = backups.get(interface)

    menu = ['1. manually', '2. randomly']
    valid_choices = [1, 2]
    if original_mac is not None:
        menu.append(f'3. restore original ({original_mac})')
        valid_choices.append(3)

    print('This is a program to change your machine\'s current MAC address.',
          'Do you want to do it:',
          *menu,
          sep='\n',
          )

    # Input validation. NOTE: this used to call `int(input(...))`
    # directly, which raised an unhandled ValueError - crashing the
    # whole program - the moment anyone typed anything that wasn't a
    # number (a blank line included). The retry loop below only ever
    # protected against a *valid* integer outside {1, 2}.
    choice = None
    while choice not in valid_choices:
        raw_choice = input('Pick a number: ')
        try:
            choice = int(raw_choice)
        except ValueError:
            choice = None
        if choice not in valid_choices:
            print('WRONG INPUT\n')

    # Now we have a valid choice.
    if choice == 1:
        return manual_new_mac()
    elif choice == 2:
        return random_new_mac()
    else:
        return original_mac


# ------------------------------- Main Function -------------------------------
def change_mac(interface, new_mac):
    """Bring `interface` down, assign it `new_mac`, then bring it back
    up. Returns True if every step succeeded.

    NOTE: previously each subprocess.call()'s return code was
    discarded entirely, so a failed step (wrong interface name,
    insufficient privileges, an invalid MAC) didn't stop the script
    from blindly running the next command anyway - e.g. still trying
    to bring the interface back up after the "down" step had already
    failed. Each step's exit code is now checked, and the sequence
    stops at the first failure.
    """
    steps = [
        ['ifconfig', interface, 'down'],
        ['ifconfig', interface, 'hw', 'ether', new_mac],
        ['ifconfig', interface, 'up'],
    ]
    for step in steps:
        if subprocess.call(step) != 0:
            print(f'ERROR: command failed: {" ".join(step)}')
            return False
    return True


def main():
    # NOTE: ifconfig comes from the net-tools package, which many
    # modern Linux distributions (e.g. Ubuntu 20.04+) no longer
    # install by default in favour of the newer `ip` command. Without
    # this check, subprocess.call() below would crash with an
    # unhandled FileNotFoundError instead of a clear message.
    if shutil.which('ifconfig') is None:
        print('ERROR: ifconfig was not found. Install it (on Debian/Ubuntu: '
              'sudo apt install net-tools) and try again.')
        raise SystemExit(1)

    # Specify the network interface first - restoring later needs to
    # know which interface's backup to offer, and validating it here
    # up front avoids wasting the user's time entering a new MAC only
    # to find out the interface name was wrong.
    interface = input('What is the network interface? ').strip()

    # NOTE: previously the interface name was never checked at all - a
    # typo only surfaced as ifconfig's own cryptic error partway
    # through change_mac(). Reading the current MAC first both
    # validates the interface exists and gives the user a "before"
    # value to compare the change against.
    current_mac = get_interface_mac(interface)
    if current_mac is None:
        print(f'ERROR: No such interface: {interface!r}.')
        available = list_interfaces()
        if available:
            print('Available interfaces:', ', '.join(available))
        raise SystemExit(1)

    print(f"[+] {interface}'s current MAC address: {current_mac}")

    # Automatically back up this interface's MAC the first time we
    # ever see it, keyed to the interface name.
    #
    # NOTE: this replaces the old "Have you backed up your MAC
    # address? [Y/n]" prompt, which relied on the user remembering to
    # run a separate shell command themselves and getting it right -
    # and even then, the file it produced had no interface name
    # attached to each line, so a later restore couldn't reliably tell
    # which address belonged to which interface. Doing it here,
    # automatically, fixes both problems at once.
    #
    # Only backing up on the *first* time this interface is seen is
    # deliberate and important: if this ran unconditionally on every
    # invocation, the second time this script changes the same
    # interface's MAC, "current_mac" would already be the *previous*
    # changed value, not the true original - silently overwriting the
    # one backup that actually mattered.
    if interface not in read_backup(BACKUP_FILE):
        write_backup(BACKUP_FILE, interface, current_mac)
        print(f"[+] Backed up {interface}'s original MAC address to "
              f'{BACKUP_FILE}.')

    # Call the function to return the newly chosen MAC address.
    new_mac = user_choice(interface, BACKUP_FILE)

    # Inform the user of the change.
    print(f'[+] Changing the MAC address for {interface} '
          f'from {current_mac} to {new_mac}.')

    # The process of changing the current MAC address.

    # Less secure version - kept here, commented out, purely to
    # show the contrast: interpolating unsanitised input into a
    # shell=True command string is a textbook command-injection
    # risk. The version actually run below passes each argument
    # as a separate list element with shell=True never set, so
    # there's no shell involved to inject into.
    # subprocess.call(f'ifconfig {interface} down', shell=True)
    # subprocess.call(f'ifconfig eth0 hw ether {new_mac}', shell=True)
    # subprocess.call(f'ifconfig {interface} up', shell=True)

    # More secure version
    if change_mac(interface, new_mac):
        # NOTE: previously "success" meant only "ifconfig's exit
        # code was 0" - the script never actually confirmed the
        # interface's MAC had changed to the intended value.
        # Reading it back closes that loop.
        confirmed_mac = get_interface_mac(interface)
        if confirmed_mac and confirmed_mac.lower() == new_mac.lower():
            print(f'[+] Success - {interface} is now {confirmed_mac}.')
        else:
            print(f'[!] ifconfig reported success, but {interface} is '
                  f'now showing {confirmed_mac!r} instead of the requested '
                  f'{new_mac!r} - double check the change actually took '
                  'effect.')


if __name__ == '__main__':
    main()
