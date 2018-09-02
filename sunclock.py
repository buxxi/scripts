#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Turns on/off a tellstick device on sunrise and sundown

Install dependencies by typing:
    pip3 install astral
    pip3 install tellcore-py
"""

import sys
import os
import pytz
from datetime import datetime
from astral import Astral
from tellcore.telldus import TelldusCore


class DeviceControl:
    def __init__(self, id):
        devices = TelldusCore().devices()

        devices = [d for d in devices if d.id == id]
        if len(devices) == 1:
            self.device = devices[0]
        else:
            raise Exception("No such device")

    def turn_on(self):
        print("Turning on")
        self.device.turn_on()

    def turn_off(self):
        print("Turning off")
        self.device.turn_off()


class StateFile:
    def __init__(self, path):
        self.path = path

    def time(self):
        if os.path.exists(self.path):
            return datetime.fromtimestamp(os.path.getmtime(self.path))
        else:
            return None

    def touch(self):
        with open(self.path, 'a'):
            os.utime(self.path, None)


class SunClock:
    def __init__(self, city):
        self.city = city

    def bright(self, d):
        a = Astral()
        sun = a[self.city].sun(date=d, local=True)
        d = sun["sunrise"].tzinfo.localize(d)
        morning = sun["sunrise"] + (sun["sunrise"] - sun["dawn"])  # keep the lights on longer in the morning
        evening = sun["sunset"] - (sun["dusk"] - sun["sunset"])  # turn on the lights earlier in the evening
        return d > morning and d < evening


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print ("Expected call './sunclock.py <statefile> <city> <telldus-id>'")
    else:
        state = StateFile(sys.argv[1])
        clock = SunClock(sys.argv[2])
        device = DeviceControl(int(sys.argv[3]))

        last = state.time()
        now = datetime.now()

        if last is None:
            print("No previous state file, waiting for next call")
        else:
            if clock.bright(now) and not clock.bright(last):
                device.turn_off()
            elif not clock.bright(now) and clock.bright(last):
                device.turn_on()
            else:
                print("Nothing changed, doing nothing")

        state.touch()
