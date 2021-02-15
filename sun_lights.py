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
import argparse
import time
from datetime import datetime
from astral.sun import sun
from astral.geocoder import lookup, database
from tellcore.telldus import TelldusCore


class DeviceControl:
    def __init__(self, id, times, delay):
        self.times = times
        self.delay = delay
        devices = TelldusCore().devices()

        devices = [d for d in devices if d.id == id]
        if len(devices) == 1:
            self.device = devices[0]
        else:
            raise Exception("No such device")

    def turn_on(self):
        for x in range(self.times):
            print("Turning on")
            self.device.turn_on()
            if x != self.times - 1:
                time.sleep(self.delay)

    def turn_off(self):
        for x in range(self.times):
            print("Turning off")
            self.device.turn_off()
            if x != self.times - 1:
                time.sleep(self.delay)


class StateFile:
    def __init__(self, path):
        self.path = path

    def time(self):
        if os.path.exists(self.path):
            return datetime.utcfromtimestamp(os.path.getmtime(self.path)).replace(tzinfo=pytz.UTC)
        else:
            return None

    def touch(self):
        with open(self.path, 'a'):
            os.utime(self.path, None)


class SunTimer:
    def __init__(self, city, current_date):
        self.city = lookup(city, database())
        self.sun = self.load_sun_data(current_date)

    def bright(self, check_date):
        # The time it takes for the sun to go down, activate the lights that much before it even starts to happen
        shift_time = (self.sun["sunrise"] - self.sun["dawn"])

        morning = self.sun["sunrise"] + shift_time  # keep the lights on longer in the morning
        evening = self.sun["sunset"] - shift_time  # turn on the lights earlier in the evening

        return check_date > morning and check_date < evening

    def load_sun_data(self, current_date):
        s = sun(self.city.observer, date=current_date)
        return s


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Triggers a Tellstick device to change if the state of sunrise/sunset differs from previous call")
    parser.add_argument("--file", required=True, help="The file that keeps the state")
    parser.add_argument("--city", required=True, help="The name of the city that should be checked")
    parser.add_argument("--device", required=True, type=int, help="The id of the device")
    parser.add_argument("--repeat", required=False, type=int, default=1, help="Amount of times the call should be repeated")
    parser.add_argument("--delay", required=False, type=int, default=3, help="Amount of seconds to wait between repeats")

    args = parser.parse_args()

    state = StateFile(args.file)
    timer = SunTimer(args.city, datetime.today())
    device = DeviceControl(args.device, args.repeat, args.delay)

    last = state.time()
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)

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
