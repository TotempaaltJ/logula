#!/usr/bin/python
import os
from os import path
import sys, codecs
from datetime import datetime
from string import ascii_letters

import markdown, md_extensions
from PIL import Image
from jinja2 import Environment, FileSystemLoader

# Prepare hyphen, load (or install) dictionary...
import hyphen
import hyphen.dictools
if not hyphen.dictools.is_installed('en_US'): hyphen.dictools.install('en_US')
h = hyphen.Hyphenator('en_US')

# DEFAULTS
# A list of all known image file extensions.
IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.tif')
# Common screen resolutions to fit images in (defaults are all about width).
# None means auto-adapt.
IMAGE_RESIZES = (
    480,
    #600,
    #768,
    900,
    #1080,
    #1200,
    1600,
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
    def __init__(self, title, tags, date, dirname, theme, image_resizes=IMAGE_RESIZES):
        self.title = title
        self.tags = tags
        self.date = date

        self.dirname = dirname
        self.tpl_env = Environment(
            loader=FileSystemLoader(path.join('templates', theme))
        )
        self.image_resizes = image_resizes

        if not path.isdir(dirname):
            raise ValueError("That's not a directory.")

        self.post_file = find_file(path.join(dirname, 'post.md')) or \
                         find_file(path.join(dirname, 'post.html'))
        if self.post_file is None:
            raise ValueError("No post.md or post.html file exists.")

        self.img_dir = find_dir(path.join(dirname, 'img'))
        self.static_dir = find_dir(path.join(dirname, 'static'))

        self.images = []


    def render_markdown(self):
        """Convert post_file from Markdown to HTML."""
        post = codecs.open(self.post_file, mode="r", encoding="utf-8")

        md = markdown.Markdown(extensions=[md_extensions.LogulaExt()])
        md.generator = self

        self.post_html = md.convert(post.read())
        return self.post_html


    def hyphenate(self):
        html = self.post_html
        final = html
        added_chars = 0

        text = True
        chars_left = 0
        for i, c in enumerate(html):
            if chars_left > 0:
                chars_left -= 1
                continue

            text = c == '>' if not text else not c == '<'
            if not text:
                continue

            if c in ascii_letters:
                rest = html[i:]

                last_i = 0
                for n, r in enumerate(rest):
                    if r not in ascii_letters:
                        break
                    last_i = i + n
                word = html[i:last_i+1]
                new_word = '&shy;'.join(h.syllables(word))
                if new_word == '':
                    new_word = word

                new_i = i + added_chars
                final = final[:new_i] + new_word + final[new_i+len(word):]

                added_chars += len(new_word) - len(word)
                chars_left = len(new_word)

        self.post_html = final
        print(self.post_html)
        return final


    def render_template(self):
        """Renders tempate with post data."""
        date = self.date.strftime('%A, %b %d, %Y')
        datetime = self.date.strftime('%Y-%m-%dT%H:%M:%S%z')

        post_tpl = self.tpl_env.get_template('post.html')
        html = post_tpl.render(
            title=self.title,
            tags=self.tags,
            date=date,
            datetime=datetime,
            content=self.post_html
        )

        # Write rendered HTML to file (possibly temp solution?).
        f = open(path.join(self.dirname, 'post.html'), 'w')
        f.write(html)
        f.close()

        return html


    def process_image(self, image):
        """
        Take one image, resize appropriately and convert to WebP. Returns
        names and sizes of created files.

        """
        files = []

        im = Image.open(image)
        # Create a WebP copy of the full size image as well.
        tmp_sizes = list(self.image_resizes) + [im.size[0]]
        for width in tmp_sizes:
            outfile = path.splitext(image)[0] + "." + str(width)

            tmp_im = im.copy()
            # Find the proper height (maintaining ratio) for this width.
            ratio = width/tmp_im.size[0]
            height = tmp_im.size[1]*ratio

            # Resize and save image.
            tmp_im.thumbnail((width, height), Image.ANTIALIAS)
            tmp_im.save(outfile + '.webp', 'WEBP')
            files.append((outfile + '.webp', width))
        return files

if __name__ == '__main__':
    dirname = (sys.argv[1:2] or [input("What directory is the post in? ")])[0]
    title = input("Title: ")
    tags = input("Tags (comma separated): ").split(',')
    print(tags)
    date = input("Custom date? [y/N] ").lower()
    if date in ("y", "yes"):
        date = input("Date: (YYYY-MM-DDTHH:MM:SS+00:00) ")
        date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S%z')
    else:
        date = datetime.now()

    gen = PostGenerator(title, tags, date, dirname, 'totj')

    print("Converting Markdown file...")
    gen.render_markdown()
    print("Hypenating...")
    gen.hyphenate()
    print("Rendering template...")
    gen.render_template()
    print("Done!")
