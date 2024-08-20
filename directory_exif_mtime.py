#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytz
from datetime import datetime
import os
from pgmagick import Image
import argparse


class ExifDirectory:
    def __init__(self, source_path, timezone_name):
        self.source_path = os.path.abspath(source_path)
        self.timezone = pytz.timezone(timezone_name)

    def is_image(self, file):
        return file.lower().endswith('.jpg') or file.lower().endswith('.jpeg')

    def date_taken(self, path):
        img = Image(path)

        exif_time = img.attribute('exif:DateTime')
        if not exif_time or exif_time == 'unknown':
            return None
        else:
            try:
                return int(self.timezone.localize(datetime.strptime(exif_time, '%Y:%m:%d %H:%M:%S')).timestamp())
            except:
                print("Invalid DateTime in EXIF for %s" % path)
                return None

    def update(self):
        print("Traversing %s for updates" % self.source_path)

        paths = []
        for root, dirs, files in os.walk(self.source_path):
            paths.append((root, files, os.stat(root).st_mtime))

        #Newest created folders first
        paths.sort(key=lambda a: a[2], reverse=True)

        for p in paths:
            self.update_dir(p[0], p[1])
    
    def update_dir(self, root, files):
        max_date = None
        for file in files:
            if self.is_image(file):
                path = os.path.abspath(os.path.join(root, file))
                date = self.date_taken(path)
                max_date = max(max_date, date) if max_date and date else date
                if date:
                    self.update_utime(path, date)

        if max_date:
            self.update_utime(root, date)

    def update_utime(self, path, date):
        current = os.stat(path)
        
        if int(current.st_mtime) != date:
            print ("Setting %s to %s" % (path, date))
            os.utime(path, (date, date))
        else:
            print ("Already correct for %s " % path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Updates files modified time to date saved in the EXIF data")
    parser.add_argument("--source", required=True, help="The source folder to read from")
    parser.add_argument('--timezone', required=True, help="The timezone to use")

    args = parser.parse_args()

    directory = ExifDirectory(args.source, args.timezone)
    directory.update()
