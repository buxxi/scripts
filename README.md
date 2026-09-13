# Scripts

Collection of scripts I use on my machines, both server and workstation

# Nautilus context scripts
- `download_and_sync_subtitles.py`: Use subliminal to fetch subtitles for movies
- `random-media.sh`: Plays a random media file from the selected folder
- `symlink-tag-file.py`: Tag files by creating a folder for each tag and symlink to the file

## Media handling
- `directory_thumbnails.py`: a file watcher that automatically creates thumbnails in a target directory
- `tmdb_ratings_countries.py`: a script to create a json summary of all movies from a user ratings on tmdb
- `run-jellyfin.sh`: Runs Jellyfin in a container until the popup is closed

## Home automation
- `sun_lights.py`: to control my lights depending on sunset/sundown using a tellstick duo
- `ping_lights.py`: to control my lights to turn of when a specific ip-adress stops answering to ping
- `pir_power.py`: control a raspberry pis monitor power with a PIR-sensor

## MPRIS2 integration
- `mpris2_websocket.py`: server that exposes mpris2 dbus control for a machine over websocket
- `mpris2_lcd.py`: client that connects to the server mentioned above for displaying the currently playing on a lcd using a raspberry pi
- `mpris2_ir-remote.py`: client that connect to the server mentioned above for controlling a player with an ir remote

## Backup
- `idle_monitor_script_runner.py`: a script that runs scripts on system idle/screen blank using native DBus
