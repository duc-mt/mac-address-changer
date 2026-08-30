<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
# Table of Contents

- [MAC address changer](#mac-address-changer)
- [Introduction](#introduction)
- [Requirements](#requirements)
- [real_mac.txt](#real_mactxt)
- [mac_history.txt](#mac_historytxt)
- [Status](#status)
- [Command-Line Mode](#command-line-mode)
- [Output](#output)
- [Testing](#testing)
- [Development](#development)
- [Known Limitations](#known-limitations)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# MAC address changer

**Aim**: Propose A Python program that could either manually or randomly change
the machine's current MAC address, depending on user choice.

# Introduction

According to Evans, Martin and Poatsy (2020, _Technology in Action_, 16th edn.,
p. 480), each network adapter has a physical address, like a serial number on an
appliance. This address is called a media access control (MAC) address, and it's
made up of six. two-position characters, such as 01:40:87:44:79:A5. (Don't
confuse this MAC with the Apple computers of the same name.) 

The first three sets of characters (in this case, 01:40:87) specify the
manufacturer of the network adapter, and the second set of characters (in this
case, 44:79:A5) makes up a unique address.

Because all MAC addresses must be unique, there is an IEEE (Institute of
Electrical and Electronics Engineers) committee responsible for allocating
blocks of numbers to network adapter manufacturers.

IEEE 802 standards define three commonly used formats to print a MAC address in
hexadecimal digits:
- Six groups of two hexadecimal digits separated by hyphens (-), like
  01-23-45-67-89-ab
- Six groups of two hexadecimal digits separated by colons (:), like
  01:23:45:67:89:ab
- Three groups of four hexadecimal digits separated by dots (.), like
  0123.4567.89ab

# Requirements

This script only uses the Python standard library - no `pip install` is
needed to run it. It changes the interface using whichever of `ip` (from
the `iproute2` package, nearly universal on modern Linux) or `ifconfig`
(from the older `net-tools` package) is available, preferring `ip`:

```bash
sudo apt install iproute2   # provides `ip` - usually already installed
sudo apt install net-tools  # provides the older `ifconfig`, if you need it
```

The script checks for one of them on startup and prints a clear message if
neither is found, rather than crashing partway through.

# real_mac.txt

The script backs this up for you automatically - see below - so you don't
need to run anything by hand. It stores one `interface,mac` pair per line,
e.g.:

```txt
eth0,11:22:33:44:55:66
wlan0,de:ad:be:ef:00:01
```

The first time the script sees a given interface, it records that
interface's *current* MAC address here before changing anything - and only
the first time, so a later run (changing an already-changed MAC again)
can never overwrite the true original with a value that isn't original
anymore. From then on, "restore original" is offered as a menu option
whenever you run the script against that interface.

Both this file and `mac_history.txt` (below) are runtime-generated and
gitignored, not tracked in this repository - they're specific to whoever
ran the script and on which machine, so there's nothing meaningful to
commit.

# mac_history.txt

Separately from `real_mac.txt` (which only ever remembers the *true*
original), every successful change is also logged here - up to the 5 most
recent per interface, oldest dropped first. This is what "undo last
change" uses: unlike restoring the original, undo steps back through
recent changes one at a time. The format is the same `interface,mac` pair
per line, but with one line per past value rather than one per interface.

# Status

Run with `--status` to see every interface at a glance - its current MAC,
whether an original is backed up, and how many undo steps are available -
without changing anything:

```bash
sudo python main.py --status
```

```txt
INTERFACE      CURRENT MAC         ORIGINAL            UNDO STEPS
eth0           aa:bb:cc:dd:ee:ff   11:22:33:44:55:66   2
wlan0          11:22:33:44:55:66   -                   0
```

# Command-Line Mode

Running `main.py` with no arguments starts the interactive menu. Passing
`--interface` and `--mode` instead runs a single operation and exits -
useful for scripting or automation (e.g. a systemd unit or cron job that
rotates the MAC on boot):

```bash
# Random MAC
sudo python main.py --interface eth0 --mode random

# A specific MAC
sudo python main.py --interface eth0 --mode manual --mac aa:bb:cc:dd:ee:ff

# Back to the true original
sudo python main.py --interface eth0 --mode restore

# Back one step (the previous value, not necessarily the original)
sudo python main.py --interface eth0 --mode undo

# Preview any of the above without actually changing anything
sudo python main.py --interface eth0 --mode random --dry-run
```

Run `python main.py --help` for the full list of options.

# Output

![An example of successfully changing the machine's current MAC
address](output.jpg)

# Testing

Install the dev dependencies and run the test suite:

```bash
pip install -r requirements-dev.txt
pytest
```

`ifconfig`/`ip` are never actually invoked during tests - `subprocess.call()`
is mocked throughout, since running either for real needs root privileges
and would actually change the machine's network configuration.

# Development

CI runs on every pull request and push via GitHub Actions
(`.github/workflows/ci.yml`): linting (`ruff`) and tests across Python
3.10-3.12, plus a `bandit` security scan (scoped to medium severity and
above - see the comment in `ci.yml` for why the remaining low-severity
findings are expected for this kind of tool, not real issues). A weekly
CodeQL scan and Dependabot are also configured.

# Known Limitations

A round of review found and fixed several bugs:

- **Random MAC generation failed about half the time.** The script's own
  docstring acknowledged this without fixing it ("it may come up with an
  error message ... just re-run the program until no error occurs"): a
  fully random first octet has its multicast bit set on roughly half of
  all possible byte values - confirmed empirically at ~52% across 2000
  generated addresses - and a multicast address is never valid as a NIC's
  own MAC. Every generated address is now guaranteed valid by construction
  (the multicast bit is cleared and the locally-administered bit is set on
  the first octet), rather than being valid by chance.
- **Non-numeric menu input crashed the whole program.** `int(input(...))`
  was called directly with no error handling; typing anything other than a
  number at the very first prompt raised an unhandled `ValueError`.
- **A manually-entered MAC address was never validated.** Any string at
  all was accepted and passed straight to `ifconfig`, which would fail
  later with its own cryptic error instead of a clear one immediately.
- **`ifconfig` missing crashed with a raw traceback.** Many modern Linux
  distributions (Ubuntu 20.04+ included) no longer install `net-tools` by
  default, so `ifconfig` frequently just isn't there - the script now
  checks for it on startup and exits with a clear message instead.
- **Command failures were silently ignored.** Each `subprocess.call()`'s
  exit code used to be discarded, so a failed step (wrong interface name,
  insufficient privileges) didn't stop the script from blindly running the
  next command anyway - e.g. still trying to bring the interface back up
  after the "down" step had already failed. Each step's exit code is now
  checked, and the sequence stops at the first failure.
- **The network interface name was never validated.** A typo only
  surfaced as `ifconfig`'s own cryptic error partway through the change.
  It's now checked against `/sys/class/net` up front, with a clear error
  and a list of the interfaces that actually exist on the machine.
- **The backup-confirmation prompt wasn't trimmed.** Answering with extra
  whitespace (`" y "`, easy to introduce by accident) fell through to the
  "no" branch instead of being recognised as "yes".

## New: automatic backup and restore, plus before/after verification

Everything below uses nothing but stdlib file I/O (reading and writing
`/sys/class/net/<interface>/address` and `real_mac.txt` - no new
dependency):

- **The interface's original MAC is backed up automatically** the first
  time the script ever sees it, keyed to that exact interface name in
  `real_mac.txt` (see above). This replaces the old "Have you backed up
  your MAC address? [Y/n]" prompt, which relied on the user remembering
  to run a separate shell command themselves and getting it right - and
  even then, the old backup format had no interface name attached to
  each line, so there was no reliable way to later tell which address
  belonged to which interface.
- **"Restore original" is offered as a menu option** whenever a backup
  exists for the interface you're changing - `user_choice()` reads
  `real_mac.txt`, and only shows the option (with the address it would
  restore to) when there's actually something to restore.
- **The interface's current MAC is shown before changing it** - "Changing
  the MAC address for eth0 **from** 11:22:33:44:55:66 **to**
  aa:bb:cc:dd:ee:ff", not just the new value in isolation.
- **The change is verified afterward, not just assumed.** Previously
  "success" meant only "`ifconfig`'s exit code was 0" - the script never
  actually confirmed the interface's MAC had changed to the intended
  value. It's now read back and compared; a mismatch is reported clearly
  instead of silently trusted.

The one safety property that makes "restore" trustworthy: the backup is
only ever written the *first* time an interface is seen, never on
subsequent runs. If it backed up unconditionally every time, changing an
already-changed MAC a second time would silently overwrite the one
backup that actually mattered - the true original - with a value that
isn't original anymore.

## New: `ip` fallback, status view, CLI mode, dry-run, change history

Five more features, on top of everything above:

1. **Falls back to `ip` when `ifconfig` is missing** (`detect_network_tool()`)
   - and actually prefers it, since `ip` (from `iproute2`) is the one
   that's nearly universally present on modern Linux, while `ifconfig`
   (from `net-tools`) increasingly isn't installed by default. Whichever
   is available, `build_change_commands()` builds the right command
   sequence for it.
2. **`--status`** lists every interface with its current MAC, whether an
   original is backed up, and how many undo steps are available - see
   "Status" above.
3. **A non-interactive CLI mode** (`--interface`/`--mode`) - see
   "Command-Line Mode" above - for scripting and automation.
4. **`--dry-run`** previews what a CLI-mode operation would do without
   changing anything or touching `real_mac.txt`/`mac_history.txt`.
5. **Change history and "undo last change"**, distinct from "restore
   original" - see "mac_history.txt" above. Every successful change is
   logged (capped at 5 entries per interface); undoing pops the most
   recent one and applies it, without pushing a new entry of its own -
   so repeated undos step further back, but there's no "redo" once
   something's been undone. This is a deliberate simplification, not an
   oversight.

**A bug found while building and testing #5**: the interactive menu
originally hardcoded "3. restore original" and "4. undo last change" as
fixed option numbers. When only one of the two was actually available
(e.g. history exists but no backup does), the *other* number was still
skipped - option "3" simply wasn't offered, but the input loop kept
re-prompting for a valid number until one was given. Scripted or
copy-pasted input using the "wrong" number (rejected, unlike a live user
who'd just try again) looped forever instead of failing once with a clear
error. Confirmed directly: a test using input `'4'` for undo when no
backup existed hung until killed. Fixed by numbering the menu dynamically
based on what's actually offered, rather than reserving fixed numbers for
options that might not appear.
