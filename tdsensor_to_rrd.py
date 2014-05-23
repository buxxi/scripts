import os
import sys
from pyrrd.rrd import RRD
from tellcore.telldus import TelldusCore, Sensor

def get_sensor(id):
	sensors = [d for d in TelldusCore().sensors() if d.id == id]
	if len(sensors) == 1:
		return sensors[0]
	else:
		raise Exception("No such sensor")

def get_rrd(name):
	if os.path.exists(name):
		return RRD(name, mode = 'r')
	else:
		raise Exception("No such RRD")

def update_rrd(sensorid, rrdfile):
	sensor = get_sensor(sensorid)
	rrd = get_rrd(rrdfile)
	value = sensor.temperature()
	rrd.bufferValue(value.timestamp, value.value)
	rrd.update()
	
if __name__ == "__main__":
	if len(sys.argv) != 3:
		print "Expected call 'python tdsensor_to_rrd.py <sensorid> <rrdfile>'"
	else:
		update_rrd(int(sys.argv[1]), sys.argv[2])
