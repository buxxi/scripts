#!/usr/bin/env python

import dbus
import gobject
import re
import threading
import json
import logging
import argparse

from dbus.mainloop.glib import DBusGMainLoop
from wsgiref.simple_server import make_server
from ws4py.server.wsgirefserver import WSGIServer, WebSocketWSGIRequestHandler
from ws4py.server.wsgiutils import WebSocketWSGIApplication
from ws4py.websocket import WebSocket
from netaddr import IPNetwork, IPAddress

'''
Exposes the MPRIS2 DBUS functionality over WebSockets.
It sends a message when a player starts/pauses and can receive commands for playing/pausing/next/previous.

Install dependencies by typing:
	pip install ws4py
	pip install netaddr
'''

logger = logging.getLogger('mpris2_websocket')

'''
A class representing a MPRIS2 Player, it can be controlled and read status from.
The player needs to be started for this to not cause exceptions on method calls.
'''
class PlayerControl:
	def __init__(self, name, player):
		self.control = dbus.Interface(player, dbus_interface='org.mpris.MediaPlayer2.Player')
		self.properties = dbus.Interface(player, dbus_interface='org.freedesktop.DBus.Properties')

	def is_playing(self):
		try:
			return self.properties.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus') == 'Playing'
		except:
			return False

	def artist(self):
		m = self.metadata()
		if 'xesam:artist' in m:
			return ' '.join(m['xesam:artist'])
		else:
			return None

	def title(self):
		m = self.metadata()
		if 'xesam:title' in m:
			return m['xesam:title']
		else:
			return None

	def length(self):
		return self.metadata()['mpris:length'] / 1000000

	def current_position(self):
		#Spotify always reports 0 here, ca we query it in another way?
		return self.properties.Get('org.mpris.MediaPlayer2.Player', 'Position') / 1000000

	def play(self):
		self.control.Play()

	def pause(self):
		self.control.Pause()

	def stop(self):
		self.control.Stop()

	def next(self):
		self.control.Next()

	def previous(self):
		self.control.Previous()

	def metadata(self):
		return to_plain_objects(self.properties.Get('org.mpris.MediaPlayer2.Player', 'Metadata'))

	def __str__(self):
		return self.properties.Get('org.mpris.MediaPlayer2', 'Identity')

'''
The class that listens to the DBUS for events regarding the different MediaPlayers.
Every time it gets an event it tries to update which player that should be treated as the currently playing (or the one that last played something).
It the calls its listener for what type of events that should be sent to all the listening clients.
'''
class PlayerListener:
	def __init__(self, bus, listener):
		self.bus = bus
		self.resolve_active_player()
		self.listener = listener
		self.previous_event = {}

	def signal_handler(self, *args):
		#VLC sends a numeric event every time the time should be updated and Spotify sends multiple of the same events on startup, ignore those
		if type(args[0]) != dbus.String or dbus.String('PlaybackStatus') not in args[1] or args[1] == self.previous_event:
			return

		self.previous_event = to_plain_objects(args[1])
		self.resolve_active_player()
		if not self.active_player:
			self.listener.no_player()
		elif self.active_player.is_playing():
			self.listener.playing(self.active_player)
		else:
			self.listener.paused(self.active_player)

	def resolve_active_player(self):
		found_any = False
		for service in self.bus.list_names():
			if re.match('org.mpris.MediaPlayer2.', service):
				found_any = True
				player = PlayerControl(service, self.bus.get_object(service, '/org/mpris/MediaPlayer2'))

				if player.is_playing():
					logger.info('Changing player %s' % (player))
					self.active_player = player
					break
		if not found_any:
			logger.info('No player active')
			self.active_player = None

'''
The class that manage all the websockets that gets created by the WebSocketServer.
It register itself as a listener to the DBUS and forwards all events to the list of websockets that has been created.
It also forwards events from the websockets to the DBUS MediaPlayer.
'''
class SocketHandler():
	def __init__(self, network_mask):
		bus = dbus.SessionBus(mainloop=DBusGMainLoop())
		self.sockets = []
		self.listener = PlayerListener(bus, self)
		self.previous_message = None
		self.network_mask = network_mask

		bus.add_signal_receiver(self.listener.signal_handler, path = '/org/mpris/MediaPlayer2')

	def create_websocket(self, sock, protocols=None, extensions=None, environ=None, heartbeat_freq=None):
		ip = sock.getpeername()[0]
		if IPAddress(ip) not in IPNetwork(self.network_mask):
			#TODO: this could probably send a 401 somehow...
			raise Exception("%s is not allowed to connect" % (ip))
		return ClientWebSocket(self, sock, protocols, extensions, environ, heartbeat_freq)

	def received_message(self, client, message):
		try:
			data = json.loads(message.data)
			dispatcher = {
				"play" : self.play,
				"pause" : self.pause,
				"stop" : self.stop,
				"next" : self.next,
				"previous" : self.previous
			}
			try:
				dispatcher[data['action']]()
			except KeyError:
				self.unknown_action(data['action'])
		except:
			logger.error("Error handling message %s" % (message.data))


	def play(self):
		self.listener.active_player.play()

	def pause(self):
		self.listener.active_player.pause()

	def stop(self):
		self.listener.active_player.stop()

	def next(self):
		self.listener.active_player.next()

	def previous(self):
		self.listener.active_player.previous()

	def unknown_action(self, action):
		logger.error("unknown action %s" % (action))

	def no_player(self):
		self.send_all({
			"no_player" : True
		})

	def playing(self, player):
		self.send_all({
			"playing" : {
				"artist" : player.artist(),
				"title" : player.title(),
				"time" : {
					"current" : player.current_position(),
					"length" : player.length()
				},
				"player" : str(player)
			}
		})

	def paused(self, player):
		self.send_all({
			"paused" : {
				"player" : str(player)
			}
		})

	def resend(self, socket):
		if self.previous_message:
			socket.send(self.previous_message)

	def send_all(self, message):
		message = json.dumps(message)
		self.previous_message = message
		logger.debug("Sending %s to %s clients" % (message, len(self.sockets)))
		for socket in self.sockets:
			socket.send(message)

'''
An implementation of the WebSocket so we can have the WebSocket in a container instead of just created by the WebSocketServer directly.
When a new WebSocket is opened it resends the previous event so we don't have to wait for a new event before the client gets any data.
'''
class ClientWebSocket(WebSocket):
	def __init__(self, parent, sock, protocols, extensions, environ, heartbeat_freq):
		super(ClientWebSocket, self).__init__(sock, protocols, extensions, environ, heartbeat_freq)
		self.parent = parent

	def opened(self):
		self.parent.sockets.append(self)
		self.parent.resend(self)

	def closed(self, code, reason=None):
		self.parent.sockets.remove(self)

	def received_message(self, message):
		self.parent.received_message(self, message)

'''
Method for converting into plain python objects, just felt to hard to work with all the wrapper objects
'''
def to_plain_objects(input):
	if type(input) == dbus.Dictionary:
		result = dict()
		for key in input:
			result[str(key)] = to_plain_objects(input[key])
		return result
	elif type(input) == dbus.Array:
		return [to_plain_objects(a) for a in input]
	elif type(input) in [dbus.String, dbus.ObjectPath]:
		return unicode(input)
	elif type(input) in [dbus.Int32, dbus.UInt32, dbus.UInt64, dbus.Int64]:
		return int(input)
	elif type(input) == dbus.Boolean:
		return int(input) == 1
	elif type(input) == dbus.Double:
		return float(input)
	else:
		logger.error(str(input))
		raise Exception(type(input))

'''
Some loop stuff required to listen to DBUS signals
'''
def main_loop_init():
	logger.info("Starting mainloop")
	loop = gobject.MainLoop()
	gobject.threads_init()
	thread = threading.Thread(target=loop.run)
	thread.daemon = True
	thread.start()

'''
Start the websocket server and also create the required DBUS listener
The network mask and port can be configured to make it only available to clients in the desired subnet.
'''
def socket_server_init(network_mask, port):
	logger.info("Starting websocket server")
	socket_handler = SocketHandler(network_mask)
	server = make_server('', port, server_class=WSGIServer, handler_class=WebSocketWSGIRequestHandler,app=WebSocketWSGIApplication(handler_cls=socket_handler.create_websocket))
	server.initialize_websockets_manager()

	try:
		server.serve_forever()
	except KeyboardInterrupt:
		server.server_close()

'''
Only start the server if its called as standalone and not loaded as a module.
Parse arguments for network mask and port or use the defaults
'''
if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('-n', '--netmask', metavar='HOST', default='127.0.0.1', help='the network mask that clients are allowed to connect from')
	parser.add_argument('-p', '--port', help='the port to listen on', default=9000, type=int)
	args = parser.parse_args()

	logging.basicConfig(level=logging.INFO)
	main_loop_init()
	socket_server_init(args.netmask, args.port)
