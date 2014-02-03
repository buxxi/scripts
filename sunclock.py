import sys
import os
import pytz
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

	def turn_off(self):
		print("Turning off")
		

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


class SunClock:
	def __init__(self, city):
		self.city = city

	def bright(self, d):
		a = Astral()
		sun = a[self.city].sun(date = d, local = True)
		d = sun["sunrise"].tzinfo.localize(d)
		return d > sun["sunrise"] and d < sun["sunset"] 					


if __name__ == '__main__':
	if len(sys.argv) != 4:
		print "Expected call 'python sunclock.py <statefile> <city> <telldus-id>'"
	else:
		state = StateFile(sys.argv[1])
		clock = SunClock(sys.argv[2])
		device = DeviceControl(int(sys.argv[3]))
		
		last = state.time()		
		now = datetime.now()
		
		if last == None:
			print "No previous state file, waiting for next call"
		else:
			if clock.bright(now) and not clock.bright(last):
				device.turn_off()
			elif not clock.bright(now) and clock.bright(last):		
				device.turn_on()
			else:
				print "Nothing changed, doing nothing"

		state.touch()
		
		
		
