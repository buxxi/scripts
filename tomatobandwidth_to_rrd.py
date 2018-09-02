#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reads bandwidth usage from a tomato based router and updates a rrd file with that value

Install dependencies by typing:
    apt install python3-rrdtool
"""

import json
import re
import sys
import time

import requests
import rrdtool


class Tomato:
    def __init__(self, host, username, password, http_id):
        self.host = host
        self.username = username
        self.password = password
        self.http_id = http_id

    def get_interface_info(self, interface):
        auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        req = requests.post('http://%s/update.cgi' % self.host, data={'_http_id': self.http_id, 'exec': 'netdev'}, auth=auth)

        pattern = re.compile(r"netdev=(.*);")
        almost_json = req.text.strip()
        almost_json = pattern.match(almost_json).group(1)
        almost_json = almost_json.replace("'", "")

        for key in set(re.findall(r"(\w+)", almost_json)):
            almost_json = almost_json.replace(key, "\"%s\"" % (key))

        data = json.loads(almost_json)
        return {'rx': int(data[interface]["rx"], 0), 'tx': int(data[interface]["tx"], 0)}

    def get_bandwidth(self, interface, wait=2):
        before = self.get_interface_info(interface)
        time.sleep(wait)
        after = self.get_interface_info(interface)
        return {'rx': (after["rx"] - before["rx"]) / wait, 'tx': (after["tx"] - before["tx"]) / wait}


def update_rrd(tomato, rrdfile, direction):
    value = tomato.get_bandwidth("vlan2")[direction]

    rrdtool.update(rrdfile, 'N:%s' % value)


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print ("Expected call './tomatobandwidth_to_rrd.py <username:password@host> <http_id> <rx/tx> <rrd-file>'")
    else:
        (username, password, host) = re.search("(.*?):(.*?)@(.*)", sys.argv[1]).groups()
        tomato = Tomato(host, username, password, sys.argv[2])
        update_rrd(tomato, sys.argv[4], sys.argv[3])
