#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Turns on/off a Conbee device on sunrise and sundown

Install dependencies by typing:
    pip3 install astral
"""

import sys
import os
import pytz
import argparse
import time
import requests
from datetime import datetime
from astral.sun import sun
from astral.geocoder import lookup, database


class DeviceControl:
    def __init__(self, host, port, apikey, light_id, group_id):
        self.base_url = 'http://%s:%s/api/%s' % (host, port, apikey)
        if light_id:
            self.device_path = 'lights/%s/state' % light_id
        elif group_id:
            self.device_path = 'groups/%s/action' % group_id
        else:
            raise Exception("light or group must be set")

    def turn_on(self):
        print("Turning on")
        self.send({'on': True})

    def turn_off(self):
        print("Turning off")
        self.send({'on': False})

    def send(self, payload):
        response = requests.put("%s/%s" % (self.base_url, self.device_path), json=payload)
        if response.status_code != 200:
            raise Exception(response.text)


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
    parser = argparse.ArgumentParser(description="Triggers a ConBee light to change if the state of sunrise/sunset differs from previous call")
    parser.add_argument("--file", required=True, help="The file that keeps the state")
    parser.add_argument("--city", required=True, help="The name of the city that should be checked")
    parser.add_argument("--light", required=False, type=int, help="The id of the light")
    parser.add_argument("--group", required=False, type=int, help="The id of the group")
    parser.add_argument("--host", required=True, help="The host where the Deconz instance is running")
    parser.add_argument("--port", required=True, type=int, help="The port where thee Deconz instance is running")
    parser.add_argument("--apikey", required=True, help="The API key that should be used for Deconz")

    args = parser.parse_args()

    state = StateFile(args.file)
    timer = SunTimer(args.city, datetime.today())
    device = DeviceControl(args.host, args.port, args.apikey, args.light, args.group)

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
