from struct import *
from pyrrd.rrd import RRD
import socket, sys, time, datetime, re, os

def get_users(host, port):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.settimeout(1)
	buf = pack(">iQ", 0, datetime.datetime.now().microsecond)
	s.sendto(buf, (host, port))

	try:
		data, addr = s.recvfrom(1024)
	except socket.timeout:
		raise Exception("Could not connect to mumble server %s:%s" % (host,port))

	r = unpack(">bbbbQiii", data)
	return r[5]

def get_rrd(name):
	if os.path.exists(name):
		return RRD(name, mode = 'r')
	else:
		raise Exception("No such RRD")

def update_rrd(host, port, rrdfile):
	users = get_users(host, port)
	rrd = get_rrd(sys.argv[2])
	
	rrd.bufferValue(int(time.time()), users)
	rrd.update()	
		
		
if __name__ == '__main__':
	if len(sys.argv) < 3:
		print "Expected call: 'python mumbleusers_to_rrd.py <host>:<port> <rrdfile>"
	
	(host, port) = re.search("(.*?):(.*)", sys.argv[1]).groups()
	update_rrd(host, int(port), sys.argv[2])