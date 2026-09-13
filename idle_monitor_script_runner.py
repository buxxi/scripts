#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Run executable scripts from a directory when the system becomes idle (screen blanked) using native DBus signals.

Each script can specify a per-script interval in seconds using a top-of-file comment like:
	# @interval: 1h

Can be used as a systemd service to run scripts on idle without needing a desktop environment or X11.
The config for that could look like this:
```
[Unit]
Description=Idle Monitor Script Runner

[Service]
Type=simple
ExecStart=/home/user/scripts/idle_monitor_script_runner.py --script-dir /home/user/scripts/idle.d --data-dir /home/user/.cache/idlemonitor

[Install]
WantedBy=default.target
```
"""

import os
import time
import argparse
import logging
import threading
import subprocess
import re

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DURATION_SEARCH_LINE_COUNT = 20
DURATION_PATTERN = r'(\d+)([smhdw])'

logger = logging.getLogger('idle_monitor_script_runner')


"""Parse a duration string like '1d', '2h', '30m', or '90s' into seconds."""
def parse_duration(value):
	if not isinstance(value, str):
		raise argparse.ArgumentTypeError(f"Invalid duration: {value!r}")

	value = value.strip().lower()
	if not value:
		raise argparse.ArgumentTypeError('Duration cannot be empty')

	match = re.fullmatch(r'%s' % DURATION_PATTERN, value)
	if not match:
		raise argparse.ArgumentTypeError(f"Invalid duration '{value}'. Use forms like '1d', '2h', '30m', or '90s'")

	amount = int(match.group(1))
	unit = match.group(2).lower()
	factors = {
		's': 1,
		'm': 60,
		'h': 60 * 60,
		'd': 24 * 60 * 60,
		'w': 7 * 24 * 60 * 60,
	}
	return amount * factors[unit]

"""Read a per-script interval from the top-of-file metadata for shell and python scripts."""
def parse_script_interval(path):
	try:
		with open(path, 'r', encoding='utf-8') as fh:
			for _ in range(DURATION_SEARCH_LINE_COUNT):
				line = fh.readline()
				if not line:
					break
				match = re.fullmatch(r'#\s*@interval\s*:\s*(%s)\s*' % DURATION_PATTERN, line.strip(), re.IGNORECASE)
				if match:
					return parse_duration(match.group(1))
	except Exception:
		logger.exception("Failed to read script metadata from '%s'", path)
	return 0


"""Store the last execution timestamp for a script in a file."""
class StateFile:
	def __init__(self, path):
		self.path = path

	def read(self):
		if not os.path.exists(self.path):
			return 0
		try:
			with open(self.path, 'r') as fh:
				return int(fh.read().strip())
		except Exception:
			return 0

	def write(self):
		now = int(time.time())
		with open(self.path, 'w') as fh:
			fh.write(str(now))


"""Represent the data needed for a script."""
class ScriptEntry:
	def __init__(self, path, interval, state):
		self.path = path
		self.interval = interval
		self.state = state


"""Manage runnable scripts and trigger them when the system becomes idle."""
class IdleScriptManager:
	def __init__(self, script_dir, data_dir, interval=0):
		self.script_dir = os.path.abspath(script_dir)
		self.data_dir = os.path.abspath(data_dir)
		self.interval = int(interval)

		if not os.path.isdir(self.script_dir):
			raise FileNotFoundError(f"Script directory '{self.script_dir}' does not exist")

		os.makedirs(self.data_dir, exist_ok=True)

	def find_scripts(self):
		try:
			entries = sorted(os.listdir(self.script_dir))
		except Exception as exc:
			logger.error('Failed to list scripts: %s', exc)
			return []

		result = []
		for name in entries:
			path = os.path.join(self.script_dir, name)
			if not os.path.isfile(path) or not os.access(path, os.X_OK):
				continue

			result.append(ScriptEntry(
				path=path,
				interval=parse_script_interval(path),
				state=StateFile(os.path.join(self.data_dir, f"{name}.lastrun")),
			))

		return result

	def run_script(self, script):
		logger.info("START: executing '%s' (interval: %s)" % (script.path, script.interval))
		try:
			completed = subprocess.run([(script.path)], check=False, capture_output=True, text=True)
			if completed.stdout:
				logger.info("STDOUT from '%s':\n%s", script.path, completed.stdout.rstrip())
			if completed.stderr:
				logger.error("STDERR from '%s':\n%s", script.path, completed.stderr.rstrip())
			if completed.returncode == 0:
				script.state.write()
				logger.info("STOP: finished '%s' cleanly" % script.path)
				return
			logger.error("ERROR: '%s' exited with code %d" % (script.path, completed.returncode))
		except Exception as exc:
			logger.exception("Failed to launch '%s': %s" % (script.path, exc))

	def run_scripts(self):
		now = int(time.time())

		for script in self.find_scripts():
			last = script.state.read()
			elapsed = now - last
			interval = script.interval

			if elapsed < interval:
				logger.info("Skipping '%s': throttled (remaining %ds)", script.path, int(interval - elapsed))
				continue

			self.run_script(script)


"""Listen for DBus signals from systemd-logind and trigger the script manager when the system becomes idle."""
class IdleListener:
	def __init__(self, manager):
		self.manager = manager
		system_bus = dbus.SystemBus(mainloop=DBusGMainLoop())
		system_bus.add_signal_receiver(handler_function=self.handle_properties_changed, signal_name='PropertiesChanged', dbus_interface='org.freedesktop.DBus.Properties', bus_name='org.freedesktop.login1', path='/org/freedesktop/login1')

	def handle_properties_changed(self, _, changed_properties, __):
		if 'IdleHint' not in changed_properties:
			return

		is_idle = bool(changed_properties['IdleHint'])
		if is_idle:
			logger.info('System signaled IDLE. Checking scripts...')
			self.manager.run_scripts()


def main_loop_init():
	logger.info('Starting mainloop')
	loop = GLib.MainLoop()
	thread = threading.Thread(target=loop.run, name='GLibMainLoop')
	thread.daemon = False
	thread.start()
	return loop, thread

def main():
	parser = argparse.ArgumentParser(description='Run scripts on system idle/screen blank using native DBus')
	parser.add_argument('-s', '--script-dir', required=True, help='Directory containing executable scripts to run on idle')
	parser.add_argument('-d', '--data-dir', required=True, help='Directory to store the last execution timestamps for scripts')
	args = parser.parse_args()
	logging.basicConfig(level=logging.INFO)

	manager = IdleScriptManager(args.script_dir, args.data_dir)
	loop, thread = main_loop_init()
	IdleListener(manager)
	try:
		thread.join()
	except KeyboardInterrupt:
		logger.info('Stopping mainloop')
		loop.quit()
		thread.join()


if __name__ == '__main__':
	main()
