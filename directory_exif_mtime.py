#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytz
from datetime import datetime
import os
import exif
import pgmagick
import argparse
import re


class ExifDirectory:
    def __init__(self, source_path, timezone_name):
        self.source_path = os.path.abspath(source_path)
        self.timezone = pytz.timezone(timezone_name)

    def is_image(self, file):
        return file.lower().endswith('.jpg') or file.lower().endswith('.jpeg')

    def date_taken(self, path):
        with open(path, 'rb') as data:
            exif_time = None

            try:
                img = exif.Image(data)
                if hasattr(img, 'datetime'):
                    exif_time = img.datetime
                elif hasattr(img, 'datetime_original'):
                    exif_time = img.datetime_original
            except KeyError as e:
                img = pgmagick.Image(path)
                exif_time = img.attribute('exif:DateTime')

            if not exif_time or exif_time == 'unknown':
                return None
            else:
                try:
                    return int(self.timezone.localize(datetime.strptime(exif_time, '%Y:%m:%d %H:%M:%S')).timestamp())
                except:
                    if re.match('^[0-9]{13}$', exif_time):
                        return int(int(exif_time) / 1000)
                    m = re.match('^([0-9]{4}:[0-9]{2}:[0-9]{2}) 24:([0-9]{2}:[0-9]{2})$', exif_time)
                    if m:
                        return int(self.timezone.localize(datetime.strptime(('%s 23:%s' % (m.group(1), m.group(2))), '%Y:%m:%d %H:%M:%S')).timestamp()) + 3600
                    print("Invalid DateTime in EXIF for %s: %s" % (path, exif_time))
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
                
                if date:
                    max_date = max(max_date, date) if max_date else date
                    self.update_utime(path, date)
        
        if max_date:
            self.update_utime(root, max_date)

    def update_utime(self, path, date):
        current = os.stat(path)
        
        if int(current.st_mtime) != date:
            print ("Setting %s to %s" % (path, date))
            os.utime(path, (date, date))
        else:
            pass
            #print ("Already correct for %s " % path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Updates files modified time to date saved in the EXIF data")
    parser.add_argument("--source", required=True, help="The source folder to read from")
    parser.add_argument('--timezone', required=True, help="The timezone to use")

    args = parser.parse_args()

    directory = ExifDirectory(args.source, args.timezone)
    directory.update()
