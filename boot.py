#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
boot script, do initial stuff here, similar to the setup() function on Arduino
"""

import esp
import gc
import network
import time

# set clock speed to 240MHz instead of default 160MHz
# machine.freq(240000000)

# disable ESP os debug output
esp.osdebug(None)

station = network.WLAN(network.STA_IF)
if station.active() and station.isconnected():
    station.disconnect()
    time.sleep(1)
station.active(False)
time.sleep(1)
station.active(True)

# run garbage collector at the end to clean up
gc.collect()

print('Finished booting')
