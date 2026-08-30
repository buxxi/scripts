#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess

def resolve_tag_folder(selected_files):
    if (len(selected_files) == 0):
        return None
    current = os.path.dirname(selected_files[0])
    while current != '/':
        if os.path.isdir(os.path.join(current, 'tags')):
            return os.path.join(current, 'tags')
        current = os.path.abspath(os.path.join(current, '..'))
    return None

def get_possible_tags(tag_folder):
    return sorted([tag for tag in os.listdir(tag_folder) if os.path.isdir(os.path.join(tag_folder, tag))])

def write_tags(selected_files, selected_tags, tag_folder):
    for file in selected_files:
        for tag in selected_tags:
            write_tag(file, tag, tag_folder)

def write_tag(file, tag, tag_folder):
    filename = os.path.basename(file)
    tag_path = os.path.join(tag_folder, tag, filename)
    os.symlink(file, tag_path)

def select_tags(possible_tags):
    tags_text = [("%s %s" % (tag, tag)) for tag in possible_tags]

    result = subprocess.check_output('zenity --list --checklist --title "Add tags" --column Select --column Tag %s' % " ".join(tags_text), shell=True, text=True);

    return [tag.strip() for tag in result.split("|") if tag]

if 'NAUTILUS_SCRIPT_SELECTED_FILE_PATHS' not in os.environ:
    os.system('zenity --error --text "NAUTILUS_SCRIPT_SELECTED_FILE_PATHS not set"')
    exit()
selected_files = [file.strip() for file in os.environ['NAUTILUS_SCRIPT_SELECTED_FILE_PATHS'].split("\n") if file]

tag_folder = resolve_tag_folder(selected_files)

if not tag_folder:
    os.system('zenity --error --text "Could not locate a parent folder containing tags"')

tags = get_possible_tags(tag_folder)

selected_tags = select_tags(tags)

write_tags(selected_files, selected_tags, tag_folder)