#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Listens to IR-commands with lirc and sends commands to MPRIS2 on a remote host by connecting to a server over WebSockets (see mpris2_websocket.py).
If lirc isn't available it will listen to stdin instead.

The commands that should be mapped in lirc are the following for a program called "mpris":
	KEY_PLAY
	KEY_PAUSE
	KEY_NEXT
	KEY_PREVIOUS
	KEY_STOP

Install dependencies by typing:
	pip install ws4py
'''

import logging
import argparse
import json
import time
import threading
import random
from ws4py.client.threadedclient import WebSocketClient

logger = logging.getLogger('mpris2_remote')

'''
Check if the lirc module exists
'''
using_lirc = False
try:
	import lirc
	using_lirc = True
except ImportError as e:
	logger.error("Missing package lirc, using console instead")
	logger.error(e)

'''
Dummy implementation for debugging or when lirc is not available
'''
class KeyboardRemote:
	def init(self, name):
		pass

	def nextcode(self):
		return [raw_input("Input: ")]

	def deinit(self):
		pass

'''
Listen to the lirc service for buttons pressed on the remote
Map them to actions that our server can understand and then send them
'''
class RemoteListener:
	def __init__(self, client, identifier):
		lirc.init(identifier)
		self.client = client
		self.mapping = {
			'KEY_PLAY' : 'play',
			'KEY_PAUSE' : 'pause',
			'KEY_NEXT' : 'next',
			'KEY_PREVIOUS' : 'previous',
			'KEY_STOP' : 'stop'
		}

	def run(self):
		while (True):
			code = lirc.nextcode()
			action = self.resolve_action(code)
			logger.info("Action: %s" % (action))
			if action != None:
				self.client.send_action(action)

	def resolve_action(self, code):
		if not code:
			return None
		if code[0] not in self.mapping.keys():
			return None
		else:
			return self.mapping[code[0]]

'''
We need to implement a client but it can be really dumb,
only need to be able to send data, don't care about what we receive
'''
class PassiveClient(WebSocketClient):
	def opened(self):
		pass

	def closed(self, code, reason=None):
		pass

	def received_message(self, m):
		pass

	def send_action(self, action):
		self.send(json.dumps({ "action" : action }))

'''
Start the websocket client and a new thread that listens to commands from the remote
'''
def client_init(identifier, host, port):
	try:
		ws = PassiveClient('ws://%s:%s/' % (args.host, args.port))
		ws.connect()

		listener = RemoteListener(ws, identifier)
		thread = threading.Thread(target=listener.run)
		thread.daemon = True
		thread.start()
		ws.run_forever()
	except KeyboardInterrupt:
		ws.close()

'''
Only start the client if its called as standalone and not loaded as a module.
Parse arguments for host, port or use the defaults
'''
if __name__ == '__main__':
	try:
		parser = argparse.ArgumentParser()
		parser.add_argument('-c', '--console', metavar='console', default=False, type=bool, help='If the data should be read from console (stdin) instead')
		parser.add_argument('-n', '--host', metavar='HOST', default='127.0.0.1', help='the host to connect to')
		parser.add_argument('-p', '--port', help='the port to connect to', default=9000, type=int)
		parser.add_argument('-i', '--identifier', help='the lirc program identifier to use', default='mpris')
		args = parser.parse_args()

		if not using_lirc or args.console:
			lirc = KeyboardRemote()

		client_init(args.identifier, args.host, args.port)
	finally:
		lirc.deinit()
