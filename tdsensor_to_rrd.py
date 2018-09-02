#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reads a value from a tellstick device and updates a rrd file with that value

Install dependencies by typing:
    apt install python3-rrdtool
"""

import sys
import rrdtool
from tellcore.telldus import TelldusCore


def get_sensor(id):
    sensors = [d for d in TelldusCore().sensors() if d.id == id]
    if len(sensors) == 1:
        return sensors[0]
    else:
        raise Exception("No such sensor")


def update_rrd(sensorid, rrdfile):
    sensor = get_sensor(sensorid)
    value = sensor.temperature()

    rrdtool.update(rrdfile, 'N:%s' % value)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print ("Expected call './tdsensor_to_rrd.py <sensorid> <rrdfile>'")
    else:
        update_rrd(int(sys.argv[1]), sys.argv[2])
