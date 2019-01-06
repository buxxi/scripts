#!/usr/bin/env python3

import re
import os
import argparse
import codecs
from prettytable import PrettyTable

'''
Sets monitors to the same resolution with their maximum refresh rate possible in the order they are specified.
Uses monitor names instead of the port they are plugged into.
The monitor with the highest refresh rate will be the primary.

Install dependencies by typing:
	apt install python3-prettytable
'''

class Monitor:
	def __init__(self, interface):
		self.interface = interface
		self.name = None
		self.rate = None
	
	def valid(self):
		return self.name and self.rate
	
	def __repr__(self):
		return str(self.name) + "@" + str(self.rate)

def parse_monitors(mode):
	edid = None
	rate = None
	result = []
	for line in os.popen("xrandr --prop").readlines():
		line = line.strip()
		p = re.compile("([^ ]+) (dis)?connected.*")
		m = p.match(line)
		if m:
			result.append(Monitor(m.group(1)))
		elif result and mode in line:
			p = re.compile("([\\d]+)\\.[\\d]")
			result[-1].rate = max([int(x) for x in p.findall(line)])
		elif result and line == "EDID:":
			edid = " "
		elif edid:
			if re.compile("^[0-9abcdef]+$").match(line):
				edid += line
			else:
				edid = edid
				m = re.compile(".*000000fc00(.*?)0a.*")

				decode_hex = codecs.getdecoder("hex_codec")

				result[-1].name = decode_hex(m.match(edid).group(1))[0].decode('UTF-8')
				edid = None
	return [x for x in result if x.valid()]

def get_monitor(name, monitors):
	for monitor in monitors:
		if monitor.name == name:
			return monitor
	raise Exception("No monitor found with name %s" % (name))

def print_monitors(mode):
	table = PrettyTable(["Monitor", "Interface", "Max refresh rate"])
	table.align = 'l'
	for monitor in parse_monitors(mode):
		table.add_row([monitor.name, monitor.interface, "%s Hz" % (monitor.rate)])
	print (table)

def set_monitors(names, mode):
	monitors = parse_monitors(mode)
	on = []
	
	for name in names:
		monitor = get_monitor(name, monitors)
		monitors.remove(monitor)
		on.append(monitor)
	on.reverse()
	off = monitors
	
	commands = []
	primary = max([(m.rate, i) for i,m in enumerate(on)])[1]

	for monitor in off:
		commands.append("--output %s --off" % (monitor.interface))
	for i, monitor in enumerate(on):
		if i == 0 and i != primary:
			commands.append("--output %s --mode %s --rate %s" % (monitor.interface, mode, monitor.rate))
		elif i == 0 and i == primary:
			commands.append("--output %s --mode %s --rate %s --primary" % (monitor.interface, mode, monitor.rate))
		elif i >= 0 and i == primary:
			commands.append("--output %s --mode %s --rate %s --left-of %s --primary" % (monitor.interface, mode, monitor.rate, on[i -1].interface))
		else:
			commands.append("--output %s --mode %s --rate %s --left-of %s" % (monitor.interface, mode, monitor.rate, on[i -1].interface))

	os.popen('xrandr %s' % (' '.join(commands)))

if  __name__ =='__main__':
	parser = argparse.ArgumentParser(description = "Changes the layout of the monitors using the monitors names instead of interfaces")
	parser.add_argument("--mode", required=True, help = "The resolution that should be used on all the monitors")
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("--set", type=lambda s: s.split(','), metavar="MONITOR1,MONITOR2", help = "Sets the order of the monitors and makes the the highest refresh rate as primary")
	group.add_argument("--list", action="store_true", help = "Lists all the connected monitors and their interface")
	args = parser.parse_args()
	if args.list:
		print_monitors(args.mode)
	elif args.set:
		set_monitors(args.set, args.mode)
