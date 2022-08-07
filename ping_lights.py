#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Turns off a Conbee device when a machine stops answering to ping.
"""

import sys
import os
import socket
import subprocess
import argparse
import time
import requests


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
    parser = argparse.ArgumentParser(description="Triggers a Conbee light to change if the target machine stops answering to ping")
    parser.add_argument("--file", required=True, help="The file that keeps the state")
    parser.add_argument("--city", required=True, help="The name of the city that should be checked")
    parser.add_argument("--light", required=False, type=int, help="The id of the light")
    parser.add_argument("--group", required=False, type=int, help="The id of the group")
    parser.add_argument("--host", required=True, help="The host where the Deconz instance is running")
    parser.add_argument("--port", required=True, type=int, help="The port where thee Deconz instance is running")
    parser.add_argument("--apikey", required=True, help="The API key that should be used for Deconz")
    parser.add_argument("--ip", required=True, help="The host or ip of the target machine")

    args = parser.parse_args()

    state = StateFile(args.file)
    ping = PingMachine(args.ip)
    device = DeviceControl(args.host, args.port, args.apikey, args.light, args.group)

    answered_now = ping.answers()

    if state.answered_last_time() and not answered_now:
        device.turn_off()

    if answered_now:
        print ("Device answered to ping")
        state.touch()
    else:
        print ("Device did not answer to ping")
        state.remove()
