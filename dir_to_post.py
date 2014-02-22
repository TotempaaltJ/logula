#!/usr/bin/python
import os
from os import path

import sys
from string import ascii_letters
import markdown

# Prepare hyphen, load (or install) dictionary...
import hyphen
import hyphen.dictools
if not hyphen.dictools.is_installed('en_US'): hyphen.dictools.install('en_US')
h = hyphen.Hyphenator('en_US')

# DEFAULTS
# A list of all known image file extensions.
IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.tiff')
# Common screen resolutions to fit images in (defaults are all about width).
# None means auto-adapt.
IMAGE_RESIZES = (
    (None, 480),
    (None, 600),
    (None, 768),
    (None, 900),
    (None, 1080),
    (None, 1200),
    (None, 1600),
)


def find_file(filename):
    """Return filename if file exists, otherwise None."""
    if path.isfile(filename):
        return filename
    return None

def find_dir(dirname):
    """Return dir if directory exists, otherwise None."""
    if path.isdir(dirname):
        return dirname
    return None


class PostGenerator(object):
    def __init__(self, dirname):
        self.dirname = dirname

        if not path.isdir(dirname):
            raise ValueError("That's not a directory.")

        self.post_file = find_file(path.join(dirname, 'post.md')) or \
                         find_file(path.join(dirname, 'post.html'))
        if self.post_file is None:
            raise ValueError("No post.md or post.html file exists.")

        self.img_dir = find_dir(path.join(dirname, 'img'))
        self.static_dir = find_dir(path.join(dirname, 'static'))

        self.images = []

    def read_imgdir(self, extensions=IMAGE_EXT):
        """Take all images from self.img_dir and put them in self.images."""
        for entry in os.listdir(self.img_dir):
            if path.isfile(entry) \
               and entry[entry.rfind('.'):].lower() in extensions:
                self.images.append(entry)

    def process_images(self, sizes=IMAGE_RESIZES):
        """Take the images in self.images and resize them appropriately."""
        for image in self.images:
            im = Image.open(image)
            for width, height in sizes:
                if width is None:
                    pass
                if height is None:
                    pass
