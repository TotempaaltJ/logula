#!/usr/bin/python
import os
from os import path
import sys, codecs
import arrow
from string import ascii_letters

import markdown, md_extensions
from PIL import Image
from jinja2 import Environment, FileSystemLoader
import yaml
import json

# Prepare hyphen, load (or install) dictionary...
import hyphen
import hyphen.dictools
if not hyphen.dictools.is_installed('en_US'): hyphen.dictools.install('en_US')
h = hyphen.Hyphenator('en_US')

# DEFAULTS
# Common screen resolutions to fit images in (defaults are all about width).
# None means auto-adapt.
IMAGE_RESIZES = (
    480,
    640,
    700,
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
    def __init__(self, title, hero, tags, date, source, destination, dest_img_dir,
                 base_url, img_url, image_resizes=IMAGE_RESIZES, neighbours=True):
        # Post meta
        self.title = title
        self.hero = hero
        self.tags = tags
        self.date = date

        # Filesystem information
        self.source = source
        if not path.isdir(source):
            raise ValueError("Source must be a directory.")
        self.wip_dir = path.split(source)[-2]
        self.destination = destination
        self.dest_img_dir = dest_img_dir

        self.slug = path.split(source)[-1]

        # Set up Jinja2 environment.
        self.tpl_env = Environment(loader=FileSystemLoader('templates'))

        # Base URL to use for images etc. (don't trailing slash!)
        self.base_url = base_url
        self.img_url = img_url
        # List of maximum widths for images
        self.image_resizes = image_resizes
        self.neighbours = neighbours

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
        with codecs.open(self.post_file, mode="r", encoding="utf-8") as f:
            source = f.read()

        md = markdown.Markdown(extensions=[md_extensions.LogulaExt()])
        md.generator = self

        posts = os.listdir(path.join(self.destination, 'sources'))
        # We want to make sure we overwrite the post if it already existed.
        get_slug = lambda s: s[s.find('-')+1:-3]
        get_stamp = lambda s: int(s[:s.find('-')])

        equal_slug = [p for p in posts if get_slug(p) == self.slug]
        if len(equal_slug) > 0:
            filename = max(equal_slug, key=get_stamp)
            self.date = arrow.get(get_stamp(filename))
        else:
            filename = '{}-{}.md'.format(self.date.timestamp, self.slug)

        with open(path.join(self.destination, 'sources', filename), 'w+') as f:
            f.write(source)

        self.post_html = md.convert(source)
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
        hero_path = path.join(self.img_dir, self.hero)
        if path.isfile(hero_path):
            hero = self.process_image(hero_path, False)[0]
            hero = path.join(self.img_url, self.slug, path.split(hero[0])[-1])
            hero = hero.replace('\\','/') # in case of windows...
        else:
            hero = False

        date = self.date.strftime('%A, %b %d, %Y')
        datetime = self.date.strftime('%Y-%m-%dT%H:%M:%S%z')

        data = {
            'title': self.title,
            'hero': hero,
            'tags': self.tags,
            'date': date,
            'datetime': datetime,
            'content': self.post_html,
            'base_url': self.base_url,
            'newer': None,
            'older': None,
        }

        # Figure out if there's a previous or next blogpost we should include.
        timestamp = self.date.timestamp

        posts = os.listdir(path.join(self.destination, 'sources'))
        newer, older = [], []

        get_slug = lambda s: s[s.find('-')+1:-3]
        get_stamp = lambda s: int(s[:s.find('-')])
        for post in posts:
            if not post.endswith('.md'): continue
            if get_slug(post) == self.slug: continue

            if get_stamp(post) > self.date.timestamp:
                newer.append(post)
            else:
                older.append(post)
        if newer != []:
            newer_slug = get_slug(min(newer, key=get_stamp))
            data['newer'] = newer_slug + '.html'

            if self.neighbours:
                publish_post(
                    path.join(self.wip_dir, newer_slug),
                    self.destination,
                    self.dest_img_dir,
                    self.base_url,
                    self.img_url,
                    False
                )
        if older != []:
            older_slug = get_slug(max(older, key=get_stamp))
            data['older'] = older_slug + '.html'

            if self.neighbours:
                publish_post(
                    path.join(self.wip_dir, older_slug),
                    self.destination,
                    self.dest_img_dir,
                    self.base_url,
                    self.img_url,
                    False
                )

        post_tpl = self.tpl_env.get_template('post.html')
        html = post_tpl.render(**data)

        # Write rendered HTML to file (possibly temp solution?).
        filename = '{}.html'.format(self.slug)
        f = open(path.join(self.destination, filename), 'w')
        f.write(html)
        f.close()

        return html


    def render_archive(self):
        posts_dir = os.listdir(path.join(self.destination, 'sources'))
        posts = []
        for post in posts_dir:
            if not post.endswith('.md'): continue
            slug = post[post.find('-')+1:-3]
            time = arrow.get(int(post[:post.find('-')]))

            wip_dir = path.join(*self.source.split(os.sep)[:-1])
            real_src = path.join(wip_dir, slug, 'post.yaml')
            with open(real_src, 'r') as y:
                data = yaml.load(y)
                data['date'] = arrow.get(data['date'])

            posts.append(data)

        posts.sort(key=lambda p: p['date'])
        posts.reverse()

        archive_tpl = self.tpl_env.get_template('archive.html')
        html = archive_tpl.render(posts=posts)
        f = open(path.join(self.destination, 'archive.html'), 'w')
        f.write(html)

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
            outdir = path.join(self.dest_img_dir, self.slug)
            if not path.exists(outdir):
                os.makedirs(outdir)
            outfile = path.splitext(image)[0] + "." + str(width)
            outfile = path.join(outdir, path.split(outfile)[-1])
            if path.isfile(outfile + '.webp'):
                files.append((outfile + '.webp', width))
                continue

            tmp_im = im.copy()
            # Find the proper height (maintaining ratio) for this width.
            ratio = width/tmp_im.size[0]
            height = tmp_im.size[1]*ratio

            # Resize and save image.
            tmp_im.thumbnail((width, height), Image.ANTIALIAS)
            tmp_im.save(outfile + '.webp', 'WEBP')
            files.append((outfile + '.webp', width))
        return files


def publish_post(post_dir, publish_dir, img_dir, base_url, img_url, neighbours=True):
    """Loads a post from post_dir and publishes it to destination."""
    with open(path.join(post_dir, 'post.yaml'), 'r') as f:
        data = yaml.load(f)

    print(path.join(post_dir, 'post.yaml'), data.get('date'))
    gen = PostGenerator(
        data['title'],
        data.get('hero') or 'hero.jpg',
        data.get('tags') or [],
        # Current date or published date (TODO: last update? Changelog?)
        arrow.get(data.get('date') or arrow.now()),
        post_dir,
        publish_dir,
        img_dir,
        base_url,
        img_url,
        image_resizes=IMAGE_RESIZES,
        neighbours=neighbours
    )

    gen.render_markdown()
    gen.hyphenate()
    gen.render_template()
    if neighbours:
        gen.render_archive()
    return True


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

    date = data.get('date', arrow.now())
    if not isinstance(date, arrow):
        date = arrow.get(date)

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
