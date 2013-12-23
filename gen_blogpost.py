#!/usr/bin/python
import sys
from string import ascii_letters

import markdown

import hyphen
import hyphen.dictools
if not hyphen.dictools.is_installed('en_US'): hyphen.dictools.install('en_US')
h = hyphen.Hyphenator('en_US')

# Load and parse markdown.
f = open(sys.argv[1], 'r')
text = f.read()
f.close()
htmled_text = markdown.markdown(text, output_format='html5')

# This'll be a hyphenated version of the text.
final_text = htmled_text
added_chars = 0

text = True
chars_left = 0
for i, c in enumerate(htmled_text):
    if chars_left > 0:
        chars_left -= 1
        continue

    text = c == '>' if not text else not c == '<'
    if not text:
        continue

    if c in ascii_letters:
        rest = htmled_text[i:]

        last_i = 0
        for n, r in enumerate(rest):
            if r not in ascii_letters:
                break
            last_i = i + n
        word = htmled_text[i:last_i+1]
        new_word = '&shy;'.join(h.syllables(word))
        if new_word == '':
            new_word = word

        new_i = i + added_chars
        final_text = final_text[:new_i] + new_word + final_text[new_i+len(word):]

        added_chars += len(new_word) - len(word)
        chars_left = len(new_word)

print final_text
