#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import argparse
from pgmagick import Image, Blob
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

LARGE_MAX_WIDTH = 1280
LARGE_MAX_HEIGHT = 720
SMALL_WIDTH_AND_HEIGHT = 100


class NeedsRescanHandler(FileSystemEventHandler):
    def __init__(self):
        self.modifications = False

    def on_modified(self, event):
        self.modifications = True

    def on_moved(self, event):
        self.modifications = True


class ThumbnailGenerator:
    def __init__(self):
        pass

    def generate(self, source_path, small_thumb_path, large_thumb_path):
        img = Image(source_path)

        width = img.size().width()
        height = img.size().height()

        # Detect if we need to rotate the image by reading EXIF data
        orientation = 0
        if img.attribute("EXIF:Orientation") != "unknown":
            try:
                orientation = int(img.attribute("EXIF:Orientation"))
            except ValueError:
                print ("Invalid EXIF orientation, using default")

        # Strip exif data
        blob = Blob()
        img.profile("*", blob)

        # Detect if we need to resize the large thumbnail
        if width > LARGE_MAX_WIDTH:
            height = int((float(height) / width) * LARGE_MAX_WIDTH)
            width = LARGE_MAX_WIDTH
        elif height > LARGE_MAX_HEIGHT:
            width = int((float(width) / height) * LARGE_MAX_HEIGHT)
            height = LARGE_MAX_HEIGHT

        # Rescale the large thumbnail if dimensions doesn't match
        if width != img.size().width() or height != img.size().height():
            img.sample("!%sx%s" % (width, height))

        # Rotate the image if needed
        if orientation == 6:
            img.rotate(90)
        elif orientation == 8:
            img.rotate(-90)
        elif orientation == 3:
            img.rotate(180)

        self.write_image(img, large_thumb_path)

        # Crop the small thumbnail and then resize it to the correct size
        img.crop("%sx%s" % (min(width, height), min(width, height)))
        img.sample("%sx%s" % (SMALL_WIDTH_AND_HEIGHT, SMALL_WIDTH_AND_HEIGHT))

        self.write_image(img, small_thumb_path)

    def write_image(self, img, path):
        # Create the directory tree and then write the image
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        img.write(path)


class CompositeThumbnailDirectory:
    def __init__(self, source_paths):
        self.thumbs = [ThumbnailDirectory(source_path, args.target) for source_path in source_paths]

    def observe(self, observer):
        for thumb in self.thumbs:
            thumb.observe(observer)

    def update(self, generator):
        for thumb in self.thumbs:
            thumb.update(generator)

    def needs_update(self):
        result = False
        for thumb in self.thumbs:
            result = result or thumb.needs_update()

        return result


class ThumbnailDirectory:
    def __init__(self, source_path, target_path):
        self.source_path = os.path.abspath(source_path)
        self.target_path = os.path.abspath(target_path)
        self.event_handler = NeedsRescanHandler()

    def needs_update(self):
        return self.event_handler.modifications

    def observe(self, observer):
        print("Started observing %s for updates" % self.source_path)
        observer.schedule(self.event_handler, path=self.source_path, recursive=True)

    def small_path(self, relative_path):
        return os.path.join(self.target_path, os.path.dirname(relative_path), 'small', os.path.basename(relative_path))

    def large_path(self, relative_path):
        return os.path.join(self.target_path, os.path.dirname(relative_path), 'large', os.path.basename(relative_path))

    def thumbs_exists(self, relative_path):
        return os.path.exists(self.small_path(relative_path)) and os.path.exists(self.large_path(relative_path))

    def is_image(self, file):
        return file.lower().endswith('.jpg') or file.lower().endswith('.jpeg')

    def update(self, generator):
        # Update event handler so it wont be run again if no changes has occured
        self.event_handler.modifications = False

        print("Traversing %s for updates" % self.source_path)

        # Go through the whole directory and find image files that doesn't have a thumbnail and then generate them
        for root, dirs, files in os.walk(self.source_path):
            for file in files:
                if self.is_image(file):
                    absolute_path = os.path.abspath(os.path.join(root, file))
                    relative_path = os.path.relpath(absolute_path, self.source_path)
                    if not self.thumbs_exists(relative_path):
                        try:
                            generator.generate(
                                os.path.join(self.source_path, relative_path),
                                self.small_path(relative_path),
                                self.large_path(relative_path)
                            )
                            print ("Generated thumbs for %s" % relative_path)
                        except RuntimeError as e:
                            print ("Error generating thumbs for %s: %s" % (relative_path, e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitors a folder and subfolders for images and generates thumbnails in a target folder")
    parser.add_argument("--source", action='append', required=True, help="The source folder to read from")
    parser.add_argument('--target', required=True, help="The target folder to save the thumbnails in")
    parser.add_argument("--init", action="store_true", default=False, help="Makes an initial check on start")
    parser.add_argument("--sleep", type=int, default=10, help="Time to sleep between checks if an event has happened")

    args = parser.parse_args()

    generator = ThumbnailGenerator()

    # Merge multiple source-paths to a list of generators
    thumbs = CompositeThumbnailDirectory(args.source)

    # Check if an update should trigger at start
    if args.init:
        thumbs.update(generator)

    # Observe all changes in the source folders
    observer = Observer()
    thumbs.observe(observer)
    observer.start()

    # Only start the generating of thumbnails in intervals, not every time a file is changed
    try:
        while True:
            if thumbs.needs_update():
                thumbs.update(generator)
            time.sleep(args.sleep)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
