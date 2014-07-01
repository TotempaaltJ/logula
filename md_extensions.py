#!/usr/bin/python
import os
from os import path

from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern, IMAGE_LINK_RE
from markdown.util import etree


class ImagePattern(Pattern):
    def handleMatch(self, m):
        gen = self.markdown.generator
        figure = etree.Element('figure')
        picture = etree.SubElement(figure, 'picture')

        src_parts = m.group(9).split()
        alt = m.group(2)
        picture.set('alt', alt)

        if src_parts:
            src = src_parts[0]

            files = gen.process_image(path.join(gen.img_dir, src))
            for f, size in files:
                f = f.split(os.sep)[-2:]
                f = path.join(gen.img_url, *f).replace('\\','/')

                # Create a source element for every resized image.
                if size in gen.image_resizes:
                    source = etree.SubElement(picture, 'source')
                    source.set('src', f)

                    # No media attribute for smallest image.
                    if size != min(gen.image_resizes):
                        source.set('media', '(min-width:{}px)'.format(size))

                    # Largest is default too
                    if size == max(gen.image_resizes):
                        noscript = etree.SubElement(picture, 'noscript')
                        img = etree.SubElement(noscript, 'img')
                        img.set('src', f)
                        img.set('alt', alt)

        return figure


class LogulaExt(Extension):
    def extendMarkdown(self, md, md_globals):
        del md.inlinePatterns['image_link']
        del md.inlinePatterns['image_reference']

        image_pattern = ImagePattern(IMAGE_LINK_RE, md)
        md.inlinePatterns.add('image', image_pattern, '_end')
