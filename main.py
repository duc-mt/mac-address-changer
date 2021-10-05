#!/usr/bin/env python3

#
# File:         main.py
# Author:       Tan Duc Mai
# Email:        tan.duc.work@gmail.com
# Date:         4/10/2021
# Description:  Change the machine's current MAC address.
#               This program MUST be run in the Root Terminal.
#               If you choose to generate randomly, it may come up with an error message since that address is invalid.
#               In this case, just re-run the program until no error occurs.
#   I hereby declare that I completed this work without any improper help
#   from a third party and without using any aids other than those cited.
#

"""
The first module is to access the terminal for inputting user commands.
The second module contains the function which generate a new MAC address based on the user choice.
"""

import subprocess
import new_mac 


# Specify the network interface.
interface = 'eth0'

# Call the function to return the newly generated MAC address.
MAC = new_mac.UserChoice()

# Inform the user of the change.
print(f'[+] Changing the MAC address for {interface} to {MAC}.')

# The process of changing the current MAC address.

## Less secure verison 
#subprocess.call(f'ifconfig {interface} down', shell=True)
#subprocess.call(f'ifconfig eth0 hw ether {MAC}', shell=True)
#subprocess.call(f'ifconfig {interface} up', shell=True)

## More secure version
subprocess.call(['ifconfig', interface, 'down'])
subprocess.call(['ifconfig', interface, 'hw', 'ether',  MAC])
subprocess.call(['ifconfig', interface, 'up'])
