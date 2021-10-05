#!/usr/bin/env python3

#
# File:         main.py
# Author:       Tan Duc Mai
# Email:        tan.duc.work@gmail.com
# Date:         20/8/2021
# Description:  Change the machine's current MAC address.
#   I hereby declare that I completed this work without any improper help
#   from a third party and without using any aids other than those cited.
#


"""
The new_mac module contains the function required to generate a new MAC address.
"""

import new_mac 


# Inform user of the change.
print(f'[+] Changing the MAC address for {interface} to {new_mac.NewMac()}.')

# The process of changing MAC address.
subprocess.call(f'ifconfig {interface} down', shell=True)
subprocess.call(f'ifconfig eth0 hw ether {new_mac}', shell=True)
subprocess.call(f'ifconfig {interface} up', shell=True)
