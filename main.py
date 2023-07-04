#!/usr/bin/python3
# -*- coding: utf-8 -*-

# =============================================================================
#
#        FILE:  main.py
#      AUTHOR:  Tan Duc Mai <henryfromvietnam@gmail.com>
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
import subprocess

# Randomly choose a hex (or nibble) for each figure of the new MAC address.
import random


# ---------------------------- Function Definitions ---------------------------
def manual_new_mac():
    # Prompt the user to enter the MAC address.
    new_mac = input('Assign the new MAC address: ')
    return new_mac


def random_new_mac():
    # Set the initial values.
    new_mac = ''
    count = 0
    hex_val = []

    # Work out the new MAC address.
    for i in range(10):
        hex_val.append(str(i))

    for i in range(ord('a'), ord('f') + 1):
        hex_val.append(chr(i))

    for _ in range(6):
        for _ in range(2):
            # Each time it iterates, one hex value is added.
            # Two iterations result in one byte.
            new_mac += random.choice(hex_val)
            count += 1
        if count % 2 == 0:
            new_mac += ':'

    # Remove the last index ':'
    new_mac = new_mac[0:-1]

    # A fruitful function.
    return new_mac


def user_choice():
    print('This is a program to change your machine\'s current MAC address.',
          'Do you want to do it:',
          '1. manually',
          '2. randomly',
          sep='\n',
          )

    choice = int(input('Pick a number: '))

    # Input validation.
    while choice not in [1, 2]:
        print('WRONG INPUT\n')
        choice = int(input('Pick a number: '))

    # Now we have a valid choice.
    if choice == 1:
        new_mac = manual_new_mac()
    else:
        new_mac = random_new_mac()

    # Fruitful function.
    return new_mac


# ------------------------------- Main Function -------------------------------
if __name__ == '__main__':
    answer = input('Have you back up your MAC address? [Y/n] ')
    if answer.lower() in ('y', 'yes', ''):
        # Call the function to return the newly generated MAC address.
        MAC = user_choice()

        # Specify the network interface.
        interface = input('What is the network interface? ')

        # Inform the user of the change.
        print(f'[+] Changing the MAC address for {interface} to {MAC}.')

        # The process of changing the current MAC address.

        # Less secure version
        # subprocess.call(f'ifconfig {interface} down', shell=True)
        # subprocess.call(f'ifconfig eth0 hw ether {MAC}', shell=True)
        # subprocess.call(f'ifconfig {interface} up', shell=True)

        # More secure version
        subprocess.call(['ifconfig', interface, 'down'])
        subprocess.call(['ifconfig', interface, 'hw', 'ether',  MAC])
        subprocess.call(['ifconfig', interface, 'up'])
    else:
        print('Please back it up!')
