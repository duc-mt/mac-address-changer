#!/usr/bin/env python3

#
# File:         new_mac.py
# Author:       Tan Duc Mai
# Email:        tan.duc.work@gmail.com
# Date:         20/8/2021
# Description:  The main working area of the dictionary.
#   I hereby declare that I completed this work without any improper help
#   from a third party and without using any aids other than those cited.
#

"""
The first module is to access the terminal for inputting commands.
The second module is to 'randomly' chooses a hex (or nibble) for each figure of the new MAC address.
"""

import subprocess
import random

def NewMac():
    # Set the initial values.
    interface = 'eth0'
    new_mac = ''
    count = 0
    hex = []

    # Work out the new MAC address.
    for i in range(10):
        hex.append(str(i))

    for j in range(ord('a'), ord('f') + 1):
        hex.append(chr(j))

    for _ in range(6):
        byte =  random.choice(hex) + random.choice(hex)
        new_mac += byte
        count += 2 
        if count % 2 == 0:
            new_mac += ':'

    # Remove the last index ':'
    new_mac = new_mac[0:-1]

    # A fruitful function
    return new_mac
