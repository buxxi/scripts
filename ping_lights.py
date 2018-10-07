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
from tellcore.telldus import TelldusCore


class DeviceControl:
    def __init__(self, id):
        devices = TelldusCore().devices()

        devices = [d for d in devices if d.id == id]
        if len(devices) == 1:
            self.device = devices[0]
        else:
            raise Exception("No such device")

    def turn_off(self):
        print("Turning off")
        self.device.turn_off()


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
    if len(sys.argv) != 4:
        print ("Expected call './ping_lights.py <statefile> <ip/host> <telldus-id>'")
    else:
        state = StateFile(sys.argv[1])
        ping = PingMachine(sys.argv[2])
        device = DeviceControl(int(sys.argv[3]))

        answered_now = ping.answers()

        if state.answered_last_time() and not answered_now:
            device.turn_off()

        if answered_now:
            print ("Device answered to ping")
            state.touch()
        else:
            print ("Device did not answer to ping")
            state.remove()
