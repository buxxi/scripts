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


class SunTimer:
    def __init__(self, city, current_date):
        self.city = city
        self.sun = self.load_sun_data(current_date)

    def bright(self, check_date):
        # The time it takes for the sun to go down, activate the lights that much before it even starts to happen
        shift_time = (self.sun["sunrise"] - self.sun["dawn"])

        morning = self.sun["sunrise"] + shift_time  # keep the lights on longer in the morning
        evening = self.sun["sunset"] - shift_time  # turn on the lights earlier in the evening
        return check_date > morning and check_date < evening

    def load_sun_data(self, current_date):
        sun = Astral()[self.city].sun(date=current_date, local=True)
        # Remove timezone stuff, local time should be the same timezone as the city requested...
        return {key: value.replace(tzinfo=None) for (key, value) in sun.items()}


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print ("Expected call './sun_lights.py <statefile> <city> <telldus-id>'")
    else:
        state = StateFile(sys.argv[1])
        timer = SunTimer(sys.argv[2], datetime.today())
        device = DeviceControl(int(sys.argv[3]))

        last = state.time()
        now = datetime.now()

        if last is None:
            print("No previous state file, waiting for next call")
        else:
            if timer.bright(now) and not timer.bright(last):
                device.turn_off()
            elif not timer.bright(now) and timer.bright(last):
                device.turn_on()
            else:
                print("Nothing changed, doing nothing")

        state.touch()
