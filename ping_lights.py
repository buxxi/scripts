#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Turns off a tellstick device when a machine stops answering to ping.

Install dependencies by typing:
    pip3 install tellcore-py
"""

import sys
import os
import socket
import subprocess
import argparse
import time
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

    def turn_off(self):
        for x in range(self.times):
            print("Turning off")
            self.device.turn_off()
            if x != self.times - 1:
                time.sleep(self.delay)


class PingMachine:
    def __init__(self, ip):
        self.ip = ip

    def answers(self):
        # To not send user input directly to a system call, lookup the ip for the hostname
        ip = socket.gethostbyname(self.ip)
        status = subprocess.call(["/bin/ping", "-c", "1", "-w", "1", ip], stdout=subprocess.PIPE)
        return status == 0


class StateFile:
    def __init__(self, path):
        self.path = path

    def answered_last_time(self):
        return os.path.exists(self.path)

    def remove(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def touch(self):
        with open(self.path, 'a'):
            os.utime(self.path, None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Triggers a Tellstick device to change if the target machine stops answering to ping")
    parser.add_argument("--file", required=True, help="The file that keeps the state")
    parser.add_argument("--host", required=True, help="The host or ip of the target machine")
    parser.add_argument("--device", required=True, type=int, help="The id of the device")
    parser.add_argument("--repeat", required=False, type=int, default=1, help="Amount of times the call should be repeated")
    parser.add_argument("--delay", required=False, type=int, default=3, help="Amount of seconds to wait between repeats")

    args = parser.parse_args()

    print(args)

    state = StateFile(args.file)
    ping = PingMachine(args.host)
    device = DeviceControl(args.device, args.repeat, args.delay)

    answered_now = ping.answers()

    if state.answered_last_time() and not answered_now:
        device.turn_off()

    if answered_now:
        print ("Device answered to ping")
        state.touch()
    else:
        print ("Device did not answer to ping")
        state.remove()
