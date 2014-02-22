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


def find_dir(source):
    """Return dir if directory exists, otherwise None."""
    if path.isdir(source):
        return source
    return None


class PostGenerator(object):
    def __init__(self, title, hero, tags, date, source, destination, base_url,
                 image_resizes=IMAGE_RESIZES):
        # Post meta
        self.title = title
        self.hero = hero
        self.tags = tags
        self.date = date

        # Filesystem information
        self.source = source
        if not path.isdir(source):
            raise ValueError("Source must be a directory.")
        self.destination = destination
        self.dirname = path.split(destination)[-1]
        if path.isdir(destination):
            raise ValueError("Destination must not exist yet!")
        os.makedirs(path.join(destination, 'img'))


        # Set up Jinja2 environment.
        self.tpl_env = Environment(loader=FileSystemLoader('templates'))

        # Base URL to use for images etc. (don't trailing slash!)
        self.base_url = base_url
        # List of maximum widths for images
        self.image_resizes = image_resizes

        # Check if there's a post file in the source directory.
        self.post_file = find_file(path.join(source, 'content.md'))
        if self.post_file is None:
            raise ValueError("No post.md file exists.")

        # Find image and static directories in source directory.
        self.img_dir = find_dir(path.join(source, 'img'))
        self.static_dir = find_dir(path.join(source, 'static'))

        self.images = []


    def render_markdown(self):
        """Convert post_file from Markdown to HTML."""
        post = codecs.open(self.post_file, mode="r", encoding="utf-8")

        md = markdown.Markdown(extensions=[md_extensions.LogulaExt()])
        md.generator = self

        self.post_html = md.convert(post.read())
        return self.post_html


    def hyphenate(self):
        """Put soft hyphenation characters in all text in the post HTML."""
        html = self.post_html
        final = html
        added_chars = 0

        text = True
        chars_left = 0
        # We have to look through all characters individually to find words
        # and filter out HTML code.
        for i, c in enumerate(html):
            if chars_left > 0:
                chars_left -= 1
                continue

            # Text is true if we're in a text part, or false if we're looking
            # at HTML.
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
        return final


    def render_template(self):
        """Renders tempate with post data and writes to destination."""
        hero = self.process_image(path.join(self.img_dir, self.hero), False)[0]
        hero = path.join(gen.base_url, gen.dirname, 'img', path.split(hero[0])[-1])

        date = self.date.strftime('%A, %b %d, %Y')
        datetime = self.date.strftime('%Y-%m-%dT%H:%M:%S%z')

        post_tpl = self.tpl_env.get_template('post.html')
        html = post_tpl.render(
            title=self.title,
            hero=hero.replace('\\','/'),
            tags=self.tags,
            date=date,
            datetime=datetime,
            content=self.post_html,
            base_url=self.base_url
        )

        # Write rendered HTML to file (possibly temp solution?).
        f = open(path.join(self.destination, 'post.html'), 'w')
        f.write(html)
        f.close()

        return html


    def process_image(self, image, resize=True):
        """
        Take one image, resize appropriately and convert to WebP. Returns
        names and sizes of created files.

        """
        files = []

        im = Image.open(image)
        # Create a WebP copy of the full size image as well.
        if resize:
            tmp_sizes = list(self.image_resizes) + [im.size[0]]
        else:
            tmp_sizes = [im.size[0]]
        for width in tmp_sizes:
            outfile = path.splitext(image)[0] + "." + str(width)
            outfile = path.join(self.destination, 'img', path.split(outfile)[-1])

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
    import yaml
    name = sys.argv[1]
    if path.isfile(name):
        f = open(name, 'r')
    elif path.isdir(name):
        f = open(path.join(name, 'post.yaml'))
    else:
        raise ValueError("That's not a directory or file.")

    data = yaml.load(f)
    f.close()

    date = data.get('date', datetime.now())
    if not isinstance(date, datetime):
        date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S%z')

    gen = PostGenerator(
        data['title'],
        data.get('hero', 'hero.jpg'),
        data.get('tags', []),
        date,
        data.get('source', name),
        data['destination'],
        data['base_url'],
        image_resizes=IMAGE_RESIZES
    )

    print("Converting Markdown file...")
    gen.render_markdown()
    print("Hypenating...")
    gen.hyphenate()
    print("Rendering template...")
    gen.render_template()
    print("Done!")
