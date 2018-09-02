#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import re
import socket
import sys
from struct import *

import rrdtool

"""
Queries a mumble server for the amount of users and updates a rrd file with that value

Install dependencies by typing:
    apt install python3-rrdtool
"""


def get_users(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1)
    buf = pack(">iQ", 0, datetime.datetime.now().microsecond)
    s.sendto(buf, (host, port))

    try:
        data, addr = s.recvfrom(1024)
    except socket.timeout:
        raise Exception("Could not connect to mumble server %s:%s" % (host, port))

    r = unpack(">bbbbQiii", data)
    return r[5]


def update_rrd(host, port, rrdfile):
    value = get_users(host, port)
    rrdtool.update(rrdfile, 'N:%s' % value)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print ("Expected call: './mumbleusers_to_rrd.py <host>:<port> <rrdfile>")
    else:
        (host, port) = re.search("(.*?):(.*)", sys.argv[1]).groups()
        update_rrd(host, int(port), sys.argv[2])
