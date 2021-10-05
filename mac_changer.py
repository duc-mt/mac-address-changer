#!/usr/bin/env python3

"""
The first module is to access the terminal for inputting commands.
The second module is to 'randomly' chooses a hex (or nibble) for each figure of the new MAC address.
"""

import subprocess
import random


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

# Inform user of the change.
print(f'[+] Changing the MAC address for {interface} to {new_mac}.')

# The process of change MAC address.
subprocess.call(f'ifconfig {interface} down', shell=True)
subprocess.call(f'ifconfig eth0 hw ether {new_mac}', shell=True)
subprocess.call(f'ifconfig {interface} up', shell=True)
