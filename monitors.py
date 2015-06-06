import re,os,argparse
from prettytable import PrettyTable

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

				result[-1].name = m.match(edid).group(1).decode("hex")
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
	print table

def set_monitors(names, mode):
	monitors = parse_monitors(mode)
	on = []
	
	for name in names:
		monitor = get_monitor(name, monitors)
		monitors.remove(monitor)
		on.append(monitor)
	on.reverse()
	on[0].primary = True
	off = monitors
	
	for monitor in off:
		os.popen("xrandr --output %s --off" % (monitor.interface))
	for i, monitor in enumerate(on):
		if i == 0:
			os.popen("xrandr --output %s --mode %s --rate %s --primary" % (monitor.interface, mode, monitor.rate))
		else:
			os.popen("xrandr --output %s --mode %s --rate %s --left-of %s" % (monitor.interface, mode, monitor.rate, on[i -1].interface))

if  __name__ =='__main__':
	parser = argparse.ArgumentParser(description = "Changes the layout of the monitors using the monitors names instead of interfaces")
	parser.add_argument("--mode", required=True, help = "The resolution that should be used on all the monitors")
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("--set", type=lambda s: s.split(','), metavar="MONITOR1,MONITOR2", help = "Sets the order of the monitors and makes the most right one the primary")
	group.add_argument("--list", action="store_true", help = "Lists all the connected monitors and their interface")
	args = parser.parse_args()
	if args.list:
		print_monitors(args.mode)
	elif args.set:
		set_monitors(args.set, args.mode)
