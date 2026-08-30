#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import os.path
import ffsubsync
import tomlkit
from ffsubsync.ffsubsync import make_parser
from subliminal import download_best_subtitles, region, save_subtitles, scan_video
from babelfish import Language

def resolve_videos():
	selected_files = [file.strip() for file in os.environ['NAUTILUS_SCRIPT_SELECTED_FILE_PATHS'].split("\n") if file]
	if len(selected_files) == 0:
		os.system('zenity --error --text "NAUTILUS_SCRIPT_SELECTED_FILE_PATHS not set"')
		exit(-1)
	return [scan_video(file) for file in selected_files]

def read_configuration(path):
	region.configure('dogpile.cache.dbm', arguments={'filename': os.path.expanduser('~/.cache/subliminal/cache.dbm')})
	with open(path, 'rb') as f:
		return tomlkit.load(f)


def download_subtitles(config, video):
	provider_configs = config['provider']
	providers = config['download']['provider']
	languages = set([Language.fromietf(l) for l in config['download']['language']])

	subtitles = download_best_subtitles([video], languages, providers=providers, provider_configs=provider_configs)[video]
	for subtitle in subtitles:
		if os.path.exists(subtitle.get_path(video)):
			continue
		save_subtitles(video, [subtitle])
	return subtitles

def sync_subtitles(video, subtitles):
	video_file_path = video.name
	count = 0
	for subtitle in subtitles:
		sync_subtitle(video_file_path, subtitle.get_path(video))
		count = count + 1
	return count

def sync_subtitle(video_file_path, subtitle_file_path):
	args = make_parser().parse_args([video_file_path, "-i", subtitle_file_path, "-o", subtitle_file_path, "--split-penalty"])
	ffsubsync.run(args)

def main():
	config = read_configuration(os.path.expanduser('~/.config/subliminal/subliminal.toml'))
	videos = resolve_videos()
	count = 0
	for video in videos:
		subtitles = download_subtitles(config, video)
		count = count + sync_subtitles(video, subtitles)
	os.system('zenity --info --text "%s subtitle(s) downloaded and synced"' % count)

try:
	main()
except Exception as e:
	os.system('zenity --error --text "Error downloading and/or syncing subtitles: %s"' % e)
	exit(-1)