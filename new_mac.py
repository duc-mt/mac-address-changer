#!/usr/bin/env python3

#
# File:         new_mac.py
# Author:       Tan Duc Mai
# Email:        tan.duc.work@gmail.com
# Date:         4/10/2021
# Description:  Manually or randomly generate a new MAC address, depending on user choice.
#   I hereby declare that I completed this work without any improper help
#   from a third party and without using any aids other than those cited.
#

"""
The first module is to access the terminal for inputting commands.
The second module is to 'randomly' choose a hex (or nibble) for each figure of the new MAC address.
"""

import subprocess
import random


def ManualNewMac():
    # Prompt the user to enter the MAC address.
    new_mac = input('Assign the new mac address: ')
    return new_mac


def RandomNewMac():
    # Set the initial values.
    new_mac = ''
    count = 0
    hex = []

    # Work out the new MAC address.
    for i in range(10):
        hex.append(str(i))

    for j in range(ord('a'), ord('f') + 1):
        hex.append(chr(j))

    for _ in range(6):
        for _ in range(2):
            # Each time it iterates, one hex value is added. Two iterations result in one byte.
            new_mac += random.choice(hex)
            count += 1 
        if count % 2 == 0:
            new_mac += ':'

    # Remove the last index ':'
    new_mac = new_mac[0:-1]

    # A fruitful function
    return new_mac 


def UserChoice():
    print ('This is a program to change your machine\'s current MAC address.',
           'Do you want to do it:',
           '1. manually',
           '2. randomly',
           sep='\n',
    )
    
    choice = int(input('Pick a number: '))
    
    # InpuValidation
    while choice not in [1, 2]:
        print('WRONG INPUT\n')
        choice = int(input('Pick a number: '))
    
    # Now we have a valid choice
    if choice == 1:
        new_mac = ManualNewMac()
    else:
        new_mac = RandomNewMac()
    
    # Fruitful function
    return new_mac

