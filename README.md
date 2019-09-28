scripts
=======

Collection of scripts I use on my machines, both server and workstation

- directory_thumbnails.py: a file watcher that automatically creates thumbnails in a target directory
- sun_lights.py : to control my lights depending on sunset/sundown using a tellstick duo
- ping_lights.py : to control my lights to turn of when a specific ip-adress stops answering to ping
- mumbleusers_to_rrd.py : connects to a mumble server and updates a local rrd-file with the number of connected users
- tdsensor_to_rrd.py : read a temperature value from tellstick and update a local rrd-file with the value
- tomatobandwidth_to_rrd.py : connects to a router running tomato firmware and writes the current bandwidth usage to a local rrd-file
- monitors.py : script for quickly changing the layout when using multiple monitors
- mpris2_websocket.py : server that exposes mpris2 dbus control for a machine over websocket
- mpris2_lcd.py : client that connects to the server mentioned above for displaying a the currently playing on a lcd using a raspberry pi
- mpris2_ir-remote.py: client that connect to the server mentioned above for controlling a player with an ir remote
- pir_power.py: control a raspberry pis monitor power with a PIR-sensor
