#!/usr/bin/python3
# -*- coding: utf-8 -*-

# =============================================================================
#
#        FILE:  main.py
#      AUTHOR:  Mai Tan Duc <ducmai.network@gmail.com>
#     CREATED:  2021-10-04
# DESCRIPTION:  Change the machine's current MAC address.
#               This program MUST be run in the Root Terminal.
#   I hereby declare that I completed this work without any improper help
#   from a third party and without using any aids other than those cited.
#
# =============================================================================


# ------------------------------- Module Imports ------------------------------
# Standard lib - access CLI scripting for inputting user commands.
import os
import shutil
import subprocess

# To parse command-line arguments for the non-interactive CLI mode.
import argparse

# Regular expressions - validate a manually-entered MAC address.
import re

# Randomly choose a hex (or nibble) for each figure of the new MAC address.
import random


# ------------------------------- Named Constant -------------------------------
# Matches the two MAC address formats ip/ifconfig actually accept: six
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
# per line, keyed by interface name (only ever the *true* original -
# see write_backup()'s "only write once per interface" rule in main).
# A module-level constant so tests can point it at a scratch file
# instead of the real one.
BACKUP_FILE = 'real_mac.txt'

# Where recent MAC changes are logged, so the *last* change can be
# undone specifically - distinct from BACKUP_FILE, which only ever
# remembers the very first (true original) value. Same "interface,mac"
# format, but multiple lines per interface are expected: each line is
# one past value, oldest first.
HISTORY_FILE = 'mac_history.txt'

# How many past values to keep per interface in HISTORY_FILE. Older
# entries are dropped as new ones are added.
MAX_HISTORY_PER_INTERFACE = 5


# ---------------------------- Function Definitions ---------------------------
def is_valid_mac(mac):
    """Return True if `mac` is a well-formed MAC address.

    Checks the shape ip/ifconfig actually accept (six colon- or
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


def read_history(filename):
    """Read the change-history file into a dict mapping each
    interface to the list of its past MAC addresses, oldest first.

    Parameters
    ----------
    filename : str
        Path to the history file (one "interface,mac" pair per line;
        unlike read_backup(), multiple lines per interface are
        expected - each one a past value, in the order they were
        recorded).

    Returns
    -------
    dict[str, list[str]]
        Empty if the file doesn't exist yet. Malformed lines are
        skipped, same reasoning as read_backup().
    """
    history = {}
    try:
        with open(filename) as f:
            for line in f:
                interface, _, mac = line.strip().partition(',')
                interface = interface.strip()
                mac = mac.strip()
                if interface and is_valid_mac(mac):
                    history.setdefault(interface, []).append(mac)
    except OSError:
        pass
    return history


def _write_history(filename, history):
    """Write a complete interface -> [mac, ...] history dict to
    `filename`, one line per entry, interfaces in sorted order and
    each interface's own entries kept in their original (oldest
    first) order. Shared by append_history() and pop_last_history()
    so the on-disk format is only ever produced in one place."""
    with open(filename, 'w') as f:
        for interface, macs in sorted(history.items()):
            for mac in macs:
                f.write(f'{interface},{mac}\n')


def append_history(filename, interface, mac,
                    max_entries=MAX_HISTORY_PER_INTERFACE):
    """Record `mac` as the most recent change-history entry for
    `interface`, trimming to the `max_entries` most recent entries for
    that interface (older ones are dropped, not the whole file)."""
    history = read_history(filename)
    entries = history.setdefault(interface, [])
    entries.append(mac)
    if len(entries) > max_entries:
        del entries[:len(entries) - max_entries]
    _write_history(filename, history)


def pop_last_history(filename, interface):
    """Remove and return the most recent history entry for
    `interface` - this is the value "undo last change" restores to.

    Returns
    -------
    str or None
        The removed MAC address, or None if there was no history for
        this interface to pop.
    """
    history = read_history(filename)
    entries = history.get(interface, [])
    if not entries:
        return None
    last = entries.pop()
    if not entries:
        del history[interface]
    _write_history(filename, history)
    return last


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


def user_choice(interface, backup_filename=BACKUP_FILE,
                 history_filename=HISTORY_FILE):
    """Ask how to set `interface`'s new MAC address: manually,
    randomly, restored to its original value (if a backup exists), or
    undone back to its previous value (if there's change history).

    Parameters
    ----------
    interface : str
        The interface the new MAC will be applied to - determines
        which of "restore original"/"undo last change" are offered,
        and which addresses they'd apply.
    backup_filename : str
        Path to the interface -> original-MAC backup file.
    history_filename : str
        Path to the interface -> past-MACs change-history file.

    Returns
    -------
    tuple[str, str]
        (new_mac, action), where action is one of 'manual', 'random',
        'restore', or 'undo' - the caller needs this to know whether
        to record the change in history (every action except 'undo')
        or consume a history entry (only 'undo') - see run_interactive().
    """
    backups = read_backup(backup_filename)
    original_mac = backups.get(interface)

    history = read_history(history_filename)
    last_mac = history[interface][-1] if history.get(interface) else None

    # NOTE: options are numbered dynamically based on what's actually
    # offered, rather than hardcoding "3. restore" / "4. undo". With a
    # fixed numbering, an interface with history but no backup (undo
    # available, restore not) would still label undo as "4" - leaving
    # a gap at "3" that no valid choice maps to. Since the retry loop
    # below re-prompts on anything not in valid_choices, mistyping (or
    # scripting) that missing number would loop forever instead of
    # just being rejected once.
    actions = [('manual', 'manually'), ('random', 'randomly')]
    if original_mac is not None:
        actions.append(('restore', f'restore original ({original_mac})'))
    if last_mac is not None:
        actions.append(('undo', f'undo last change (back to {last_mac})'))
    menu = [f'{i}. {label}' for i, (_action, label) in enumerate(actions, 1)]
    valid_choices = list(range(1, len(actions) + 1))

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
    action, _ = actions[choice - 1]
    if action == 'manual':
        return manual_new_mac(), 'manual'
    elif action == 'random':
        return random_new_mac(), 'random'
    elif action == 'restore':
        return original_mac, 'restore'
    else:
        return last_mac, 'undo'


def detect_network_tool():
    """Work out which command this system has available to change a
    network interface's MAC address.

    NOTE: this used to hardcode ifconfig only, from the net-tools
    package - which many modern Linux distributions (Ubuntu 20.04+
    included) no longer install by default, in favour of `ip` (from
    iproute2, which is nearly universally present already). `ip` is
    preferred when both are available.

    Returns
    -------
    str or None
        'ip' or 'ifconfig' (whichever is available, preferring 'ip'),
        or None if neither is.
    """
    if shutil.which('ip') is not None:
        return 'ip'
    if shutil.which('ifconfig') is not None:
        return 'ifconfig'
    return None


def build_change_commands(tool, interface, new_mac):
    """Build the sequence of commands needed to change `interface`'s
    MAC address to `new_mac`, for whichever tool is available.

    Parameters
    ----------
    tool : str
        'ip' or 'ifconfig', as returned by detect_network_tool().
    interface : str
        The interface to change.
    new_mac : str
        The MAC address to assign.

    Returns
    -------
    list[list[str]]
        Each inner list is one subprocess argv to run, in order.
    """
    if tool == 'ip':
        return [
            ['ip', 'link', 'set', 'dev', interface, 'down'],
            ['ip', 'link', 'set', 'dev', interface, 'address', new_mac],
            ['ip', 'link', 'set', 'dev', interface, 'up'],
        ]
    return [
        ['ifconfig', interface, 'down'],
        ['ifconfig', interface, 'hw', 'ether', new_mac],
        ['ifconfig', interface, 'up'],
    ]


# ------------------------------- Main Function -------------------------------
def change_mac(interface, new_mac, tool=None):
    """Bring `interface` down, assign it `new_mac`, then bring it back
    up, using whichever of ip/ifconfig is available. Returns True if
    every step succeeded.

    NOTE: previously each subprocess.call()'s return code was
    discarded entirely, so a failed step (wrong interface name,
    insufficient privileges, an invalid MAC) didn't stop the script
    from blindly running the next command anyway - e.g. still trying
    to bring the interface back up after the "down" step had already
    failed. Each step's exit code is now checked, and the sequence
    stops at the first failure.

    Parameters
    ----------
    interface : str
        The interface to change.
    new_mac : str
        The MAC address to assign.
    tool : str or None
        'ip' or 'ifconfig' to use a specific one; None (the default)
        auto-detects via detect_network_tool().
    """
    if tool is None:
        tool = detect_network_tool()
    if tool is None:
        print('ERROR: neither ip nor ifconfig is available on this system.')
        return False

    for step in build_change_commands(tool, interface, new_mac):
        if subprocess.call(step) != 0:
            print(f'ERROR: command failed: {" ".join(step)}')
            return False
    return True


def print_status():
    """List every network interface on this machine, its current MAC
    address, whether an original has been backed up for it, and how
    many change-history entries (undo steps) are available."""
    interfaces = list_interfaces()
    if not interfaces:
        print('No network interfaces found.')
        return

    backups = read_backup(BACKUP_FILE)
    history = read_history(HISTORY_FILE)

    print(f'{"INTERFACE":<15}{"CURRENT MAC":<20}{"ORIGINAL":<20}{"UNDO STEPS"}')
    for interface in interfaces:
        current = get_interface_mac(interface) or '(unavailable)'
        original = backups.get(interface, '-')
        undo_steps = str(len(history.get(interface, [])))
        print(f'{interface:<15}{current:<20}{original:<20}{undo_steps}')


def run_interactive():
    """Run the interactive, menu-driven session (the original
    behaviour of this program, extended with the features above)."""
    tool = detect_network_tool()
    if tool is None:
        print('ERROR: neither ip nor ifconfig was found. Install one (on '
              'Debian/Ubuntu: sudo apt install iproute2 - or, for the '
              'older ifconfig, sudo apt install net-tools) and try again.')
        raise SystemExit(1)

    # Specify the network interface first - restoring/undoing later
    # needs to know which interface's history to offer, and
    # validating it here up front avoids wasting the user's time
    # entering a new MAC only to find out the interface name was
    # wrong.
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
    new_mac, action = user_choice(interface, BACKUP_FILE, HISTORY_FILE)

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
    if change_mac(interface, new_mac, tool):
        # NOTE: previously "success" meant only "ifconfig's exit
        # code was 0" - the script never actually confirmed the
        # interface's MAC had changed to the intended value.
        # Reading it back closes that loop.
        confirmed_mac = get_interface_mac(interface)
        if confirmed_mac and confirmed_mac.lower() == new_mac.lower():
            print(f'[+] Success - {interface} is now {confirmed_mac}.')
        else:
            print(f'[!] ifconfig/ip reported success, but {interface} is '
                  f'now showing {confirmed_mac!r} instead of the requested '
                  f'{new_mac!r} - double check the change actually took '
                  'effect.')
            return

        # Record this change in history so it can be undone later -
        # unless this change *was* an undo, in which case the entry
        # it just consumed is removed instead. Simple stack semantics:
        # undoing doesn't push a new entry, so there's no "redo" once
        # something's been undone - a deliberate simplification.
        if action == 'undo':
            pop_last_history(HISTORY_FILE, interface)
        else:
            append_history(HISTORY_FILE, interface, current_mac)


# ------------------------------ Non-Interactive CLI ---------------------------
def build_arg_parser():
    parser = argparse.ArgumentParser(
        description='Change a network interface\'s MAC address, manually, '
                     'randomly, or by restoring/undoing a previous value. '
                     'Run with no arguments for the interactive menu.',
    )
    parser.add_argument(
        '--status', action='store_true',
        help='List every interface, its current MAC, whether an original '
             'is backed up, and how many undo steps are available, then '
             'exit.',
    )
    parser.add_argument('--interface', help='The interface to change.')
    parser.add_argument(
        '--mode', choices=['manual', 'random', 'restore', 'undo'],
        help='How to choose the new MAC. Required together with '
             '--interface.',
    )
    parser.add_argument(
        '--mac', help='The MAC address to assign. Required with '
                       '--mode manual.',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would change without actually changing it, and '
             'without recording anything to the backup/history files.',
    )
    return parser


def run_cli(args, parser, tool):
    """Run one CLI-mode operation and return a process exit code."""
    interface = args.interface
    current_mac = get_interface_mac(interface)
    if current_mac is None:
        available = list_interfaces()
        message = f'no such interface: {interface!r}'
        if available:
            message += f' (available: {", ".join(available)})'
        parser.error(message)

    backups = read_backup(BACKUP_FILE)
    history = read_history(HISTORY_FILE)

    if args.mode == 'manual':
        if not args.mac:
            parser.error('--mac is required with --mode manual')
        if not is_valid_mac(args.mac):
            parser.error(f'{args.mac!r} is not a valid MAC address '
                          '(expected six hex byte pairs separated by : '
                          'or -)')
        new_mac = args.mac
    elif args.mode == 'random':
        new_mac = random_new_mac()
    elif args.mode == 'restore':
        original_mac = backups.get(interface)
        if original_mac is None:
            parser.error(f'no backup exists yet for {interface!r}')
        new_mac = original_mac
    else:  # undo
        entries = history.get(interface, [])
        if not entries:
            parser.error(f'no change history for {interface!r} to undo')
        new_mac = entries[-1]

    if args.dry_run:
        print(f'DRY RUN: would change {interface} from {current_mac} to '
              f'{new_mac}. No changes made.')
        return 0

    print(f'Changing the MAC address for {interface} from {current_mac} '
          f'to {new_mac}.')

    if not change_mac(interface, new_mac, tool):
        return 1

    confirmed_mac = get_interface_mac(interface)
    if not (confirmed_mac and confirmed_mac.lower() == new_mac.lower()):
        print(f'ERROR: ip/ifconfig reported success, but {interface} is '
              f'now showing {confirmed_mac!r} instead of the requested '
              f'{new_mac!r} - double check the change actually took '
              'effect.')
        return 1

    print(f'Success - {interface} is now {confirmed_mac}.')

    if interface not in backups:
        write_backup(BACKUP_FILE, interface, current_mac)
        print(f"Backed up {interface}'s original MAC address to "
              f'{BACKUP_FILE}.')

    if args.mode == 'undo':
        pop_last_history(HISTORY_FILE, interface)
    else:
        append_history(HISTORY_FILE, interface, current_mac)

    return 0


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    # NOTE: this used to hardcode a check for ifconfig only - see
    # detect_network_tool()'s docstring for why that's a problem on
    # modern Linux distributions. Every path below (status, CLI mode,
    # and the interactive menu) needs this, so it's checked once here
    # rather than duplicated in each.
    tool = detect_network_tool()
    if tool is None:
        print('ERROR: neither ip nor ifconfig was found. Install one (on '
              'Debian/Ubuntu: sudo apt install iproute2 - or, for the '
              'older ifconfig, sudo apt install net-tools) and try again.')
        return 1

    if args.status:
        print_status()
        return 0

    if args.interface or args.mode:
        if not args.interface or not args.mode:
            parser.error('--interface and --mode must be given together')
        return run_cli(args, parser, tool)

    run_interactive()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
