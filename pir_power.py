#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Turns on/off the monitor power for a raspberry pi depending on a PIR sensor
The turning off is delayed for 30 seconds after no motion has been detected

Install dependencies by typing:
    apt install python3-rpi.gpio
"""

import RPi.GPIO as GPIO
import time
import threading
import subprocess

PIR_PIN = 7
DISABLE_TIMEOUT = 30

timer = None

def set_screen_power(power):
	returncode = subprocess.call('vcgencmd display_power %s' % (power),shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT) 
	if returncode != 0:
		print("Error when setting screen power")

def enable_screen():
	print("Enabling screen")
	set_screen_power(1)

def disable_screen():
	disable_timer()
	print ("Disabling screen")
	set_screen_power(0)
	

def disable_timer():
	global timer
	if not timer:
		print ("No timer to disable")
	else:
		print ("Disabling timer")
		timer.cancel()
		timer = None

def schedule_disable_screen():
	global timer
	global DISABLE_TIMEOUT
	print ("Schedule disable screen in", DISABLE_TIMEOUT)
	timer = threading.Timer(DISABLE_TIMEOUT, disable_screen)
	timer.start()


def motion_changed(pin):
	if GPIO.input(pin) == 1:
		disable_timer()
		enable_screen()
	else:
		schedule_disable_screen()

def gpio_setup():
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(PIR_PIN, GPIO.IN)
	GPIO.add_event_detect(PIR_PIN, GPIO.BOTH, callback=motion_changed)

def wait_forever():
	forever = threading.Event()
	try:
		forever.wait()
	except KeyboardInterrupt:
		exit()

if __name__ == "__main__":
	gpio_setup()
	wait_forever()	
