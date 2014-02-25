from flask import Flask, abort, request, render_template
from werkzeug.utils import secure_filename
app = Flask(__name__)

import os
from os import path
import random
from datetime import datetime
from hashlib import md5

import yaml, json
config = yaml.load(open('creator.yaml'))
import logula

# A list of all known image file extensions.
IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.tif')

CODES = []
def verify(code):
    l = (request.headers.get('User-Agent'), request.remote_addr, code)
    return l in CODES

@app.route('/')
def creator():
    return render_template('creator.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.form['username'] == config['username'] \
       and request.form['password'] == config['password']:
        user_agent = request.headers.get('User-Agent')
        ip = request.remote_addr
        salt = '{0:30x}'.format(random.randrange(16**30))

        code = user_agent + ip + salt
        code = md5(code.encode('utf-8')).hexdigest()

        CODES.append((user_agent, ip, code))
        return code
    else:
        return abort(403)

@app.route('/save', methods=['POST'])
def save():
    if not verify(request.form['code']): abort(403)

    title = request.form['title']
    slug = request.form['slug']
    content = request.form['content']

    post_dir = path.join(config['wip_dir'], slug)
    if not path.isdir(post_dir):
      os.makedirs(path.join(post_dir, 'img'))

    meta = open(path.join(post_dir, 'post.yaml'), 'w')
    yaml.dump({
        'title': title,
        'hero': '',
        'tags': [],
        'base_url': config['base_url'],
    }, meta)
    meta.close()

    content_file = open(path.join(post_dir, 'content.md'), 'w')
    content_file.write(content)
    content_file.close()

    return 'saved'

@app.route('/upload_images', methods=['POST'])
def upload_images():
    if not verify(request.form['code']): abort(403)
    slug = request.form['slug']

    file = request.files['files']
    filename = secure_filename(file.filename)
    if not path.splitext(filename)[1].lower() in IMAGE_EXT: abort(400)
    file.save(path.join(config['wip_dir'], slug, 'img', filename))

    data = {
#        'id': request.form['id'],
        'filename': filename,
    }

#  with open(path.join(config['wip_dir'], slug, 'img', filename), 'rb') as f:
#       data['image_b64'] = f.read().encode('base64')

    return json.dumps(data)

@app.route('/rename_image', methods=['POST'])
def rename_image():
    if not verify(request.form['code']): abort(403)
    if not path.splitext(request.form['new'])[1].lower() in IMAGE_EXT: abort(415)

    slug = request.form['slug']
    original = request.form['original']
    new = request.form['new']

    os.rename(
        os.path.join(config['wip_dir'], slug, 'img', original),
        os.path.join(config['wip_dir'], slug, 'img', new)
    )
    return new

@app.route('/publish', methods=['POST'])
def publish():
    if not verify(request.form['code']): abort(403)
    slug = request.form['slug']

    with open(path.join(config['wip_dir'], slug, 'post.yaml'), 'r') as f:
        yaml.load(f)

    gen = logula.PostGenerator(
        data['title'],
        data.get('hero') or 'hero.jpg',
        data.get('tags') or [],
        datetime.now(),
        path.join(config['wip_dir'], slug),
        path.join(config['publish_dir'], slug),
        data['base_url'],
        image_resizes=logula.IMAGE_RESIZES
    )

    gen.render_markdown()
    gen.hyphenate()
    gen.render_template()

    return 'published'

@app.route('/load', methods=['POST'])
def load():
    if not verify(request.form['code']): abort(403)
    slug = request.form.get('slug')
    if not slug:
        return ','.join(os.listdir(config['wip_dir']))
    else:
        with open(path.join(config['wip_dir'], slug, 'post.yaml'), 'r') as f:
            data = yaml.load(f)

        with open(path.join(config['wip_dir'], slug, 'content.md'), 'r') as f:
            data['content'] = f.read()

        data['slug'] = slug
        data['images'] = []
        for f in os.listdir(path.join(config['wip_dir'], slug, 'img')):
            if path.splitext(f)[1].lower() in IMAGE_EXT: data['images'].append(f)

        return json.dumps(data)

if __name__ == '__main__':
    app.run(debug=True)
