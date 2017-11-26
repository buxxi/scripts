#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Displays MPRIS2 currently playing on a LCD by connecting to a server over WebSockets (see mpris2_websocket.py).
This is supposed to be run on a Raspberry Pi using GPIO connected to a LCD1602A LCD 16x2.
Otherwise it will only output to the console.

All the pins are hardcoded it the main-method as seen below:
	GPIO 26	= RS
	GPIO 19	= Enable
	GPIO 13	= LCD D4
	GPIO 06	= LCD D5
	GPIO 05	= LCD D6
	GPIO 11	= LCD D7

Install dependencies by typing:
	pip install ws4py
'''

import logging
import threading
import time
import unicodedata
import json
import argparse
from ws4py.client.threadedclient import WebSocketClient

logger = logging.getLogger('mpris2_lcd')

'''
Check if the modules required to run it on the Raspberry Pi is available
'''
using_rpi = False
try:
	from RPLCD.gpio import CharLCD
	from RPi import GPIO
	using_rpi = True
except RuntimeError as e:
	logger.error("Missing packages or not a raspberry pi")
	logger.error(e)

'''
Constants for how the LCD should be updated
'''
TICKS_PER_SECOND = 2
MINIMUM_TIMEOUT_SECONDS = 3
CHARACTERS_PER_LINE = 16

'''
When not running on a Raspberry Pi (for debugging etc) this can be used instead.
It will output the data to console instead with a virtual screen in the same size as the LCD
'''
class ConsoleLCD:
	def clear(self):
		print(chr(27) + "[2J")
		pass

	def write_string(self, text):
		self.clear()
		lines = text.splitlines()
		if (len(lines) == 1):
			lines.append("")

		print("╔════════════════╗")
		print("║%s║" % (str(lines[0])))
		print("║%s║" % (str(lines[1])))
		print("╚════════════════╝")

'''
The state the screen should be in when no player is active
This is also the starting state
It will display 'No player' on the screen
'''
class NoPlayerState:
	def output(self, lcd, event):
		lcd.clear()
		lcd.cursor_mode = 'hide'
		lcd.write_string("%s\r\n%s" % (trim_or_pad("No player"), trim_or_pad("")))
		if event.wait():
			event.clear()
			return None
		else:
			return self

'''
This is the state the screen should be in when a player has been active but has been paused
It will output the player name and that it is paused
'''
class PausedState:
	def __init__(self, player):
		self.player = player

	def output(self, lcd, event):
		lcd.clear()
		lcd.cursor_mode = 'hide'
		lcd.write_string("%s\r\n%s" % (trim_or_pad(self.player), trim_or_pad("Paused")))
		if event.wait():
			return None
		else:
			return self

'''
This is the state the screen should be in when a new song has started playing (or after unpause).
It will show the player on the first row and the title on the bottom row.
If it doesn't fit it will scroll until all characters has been shown.
'''
class StartedState:
	def __init__(self, player, title, time, total):
		self.player = player
		self.title = title
		self.time = time
		self.total = total
		self.current_tick = 0
		self.duration_ticks = self.calculate_duration()

	def output(self, lcd, event):
		if not event.wait(timeout=self.ticks_as_seconds(1)):
			lcd.write_string(self.format())
			self.current_tick = self.current_tick + 1

			if self.current_tick > self.duration_ticks:
				lcd.clear()
				lcd.cursor_mode = 'hide'
				return PlayingState(self.player, self.title, self.time + self.ticks_as_seconds(self.current_tick), self.total)
			else:
				return self
		else:
			return None

	def ticks_as_seconds(self, ticks):
		return float(ticks) / TICKS_PER_SECOND

	def calculate_duration(self):
		# Find out how much time we need to show the whole title or player, otherwise use a default value
		duration = max(TICKS_PER_SECOND * MINIMUM_TIMEOUT_SECONDS, len(self.player) + 1 - CHARACTERS_PER_LINE, len(self.title) + 1 - CHARACTERS_PER_LINE)
		# The amount of ticks needs to in seconds, round it upwards
		while (duration % TICKS_PER_SECOND) != 0:
			duration = duration + 1
		return duration

	def format(self):
		return "%s\r\n%s" % (scroll_text(self.player, self.current_tick), scroll_text(self.title, self.current_tick))

'''
This is the state the screen should be in after it has displayed the initial info.
It will display the title on the first row (without scrolling).
On the second row it will display the current time to the left and the total time to the right.
Every minute it will go back to the starting state.
'''
class PlayingState:
	def __init__(self, player, title, time, total):
		self.player = player
		self.title = title
		self.time = time
		self.total = total

	def format_time(self):
		def formatter(seconds):
			minutes = int(seconds / 60)
			seconds = seconds - (minutes * 60)
			return "%02d:%02d" % (minutes, seconds)

		if (self.total == 0):
			return formatter(self.time) + (' ' * 7) + '--- '
		else:
			return formatter(self.time) + (' ' * 6) + formatter(self.total)

	def output(self, lcd, event):
		lcd.write_string("%s\r\n%s" % (trim_or_pad(self.title), self.format_time()))
		self.time = self.time + 1
		if event.wait(timeout=1):
			return None
		elif self.time % 60 == 0:
			return StartedState(self.player, self.title, self.time, self.total)
		else:
			return self

'''
The websocket client listens to the server for events and keeps track of the state for the LCD when an event is received from the server.
It also updates to a new state when it receives that from the displaying of the current state
'''
class PlayerListener(WebSocketClient):
	def __init__(self, url, lcd, event):
		WebSocketClient.__init__(self, url)
		self.lcd = lcd
		self.event = event
		self.state = NoPlayerState()

	def opened(self):
		pass

	def closed(self, code, reason=None):
		self.state = NoPlayerState()

	def received_message(self, message):
		try:
			data = json.loads(message.data)
			if 'playing' in data:
				data = data['playing']
				self.state = StartedState(to_ascii(data['player']), format_title(data['artist'], data['title']), data['time']['current'], data['time']['length'])
			elif 'no_player' in data:
				self.state = NoPlayerState()
			elif 'paused' in data:
				self.state = PausedState(to_ascii(data['paused']['player']))

			self.event.set()
		except:
			logger.error("Error handling message: %s" % (message))
			exit()

	def output(self):
		while (True):
			self.event.clear()
			new_state = self.state.output(self.lcd, self.event)
			if new_state:
				self.state = new_state

'''
Formats the artist and title into a single String
If only title exists it wont output any artist.
If both is unknown it will be empty.
'''
def format_title(artist, title):
	if artist and title:
		return "%s - %s" % (to_ascii(artist), to_ascii(title))
	elif title:
		return to_ascii(title)
	else:
		return ''

'''
If the text doesn't fit on the screen we need to trim it or otherwise pad it
This makes the text exactly CHARACTERS_PER_LINE characters long
'''
def trim_or_pad(text):
	if (len(text) > CHARACTERS_PER_LINE):
		return text[:CHARACTERS_PER_LINE]
	elif (len(text) < CHARACTERS_PER_LINE):
		return text + (' ' * (CHARACTERS_PER_LINE - len(text)))
	else:
		return text

'''
Removes characters from the text to make it fit in CHARACTERS_PER_LINE characters.
It will remove from the left, making it look like it's scrolling with increasing the units send.
If the text doesn't need scrolling it will just trim or pad it to make it fit in CHARACTERS_PER_LINE characters.
'''
def scroll_text(text, units):
	if len(text) < CHARACTERS_PER_LINE:
		return trim_or_pad(text)
	text = text + (' ' * CHARACTERS_PER_LINE)
	units = units % len(text)
	return trim_or_pad(text[units:])

'''
The LCD can only handle ascii, make it look natural by replacing 'Ö' with 'O' etc
'''
def to_ascii(text):
	normal = unicodedata.normalize('NFKD', text)
	return normal.encode('ascii', errors='ignore')

'''
Start the websocket client and a new thread that steps the state of the LCD
'''
def client_init(lcd, host, port):
	event = threading.Event()
	listener = PlayerListener('ws://@%s:%s' % (host, port), lcd, event)
	thread = threading.Thread(target=listener.output)
	thread.daemon = True
	listener.connect()
	thread.start()
	listener.run_forever()

'''
Only start the client if its called as standalone and not loaded as a module.
Parse arguments for host, port or use the defaults
'''
if __name__ == '__main__':
	try:
		parser = argparse.ArgumentParser()
		parser.add_argument('-c', '--console', metavar='console', default=False, type=bool, help='If the data should be outputted to console instead')
		parser.add_argument('-n', '--host', metavar='HOST', default='127.0.0.1', help='the host to connect to')
		parser.add_argument('-p', '--port', help='the port to connect to', default=9000, type=int)
		args = parser.parse_args()

		lcd = None
		if using_rpi and not args.console:
			lcd = CharLCD(pin_rs=26, pin_rw=7, pin_e=19, pins_data=[13, 6, 5, 11], numbering_mode=GPIO.BCM, cols=CHARACTERS_PER_LINE, rows=2)
		else:
			lcd = ConsoleLCD()

		lcd.clear()
		client_init(lcd, args.host, args.port)
	finally:
		lcd.clear()
		if using_rpi:
			GPIO.cleanup()
