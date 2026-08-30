#!/bin/bash

result=`sudo docker start jellyfin`

zenity --info --title="Jellyfin" --class="JellyfinManager" --text="Jellyfin server container is running on port 8096"

result=`sudo docker stop jellyfin`
