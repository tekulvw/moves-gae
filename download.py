"""
List of Endpoints
=================

    - :code:`/download/image`: Handled by :py:func:`.download_image`.
    - :code:`/download/video`: Handled by :py:func:`.download_video`.

API Reference
=============
"""

from flask import Flask, request, abort, redirect

import storage


def download_image():
    """
    This function expects a :code:`key` URL parameter. Key is the post's ID and corresponds to the
    filename w/o extension in Storage. This endpoint should redirect to the file's location in Storage.

    :return:
        Redirects to the file's location in Storage.
    """
    key = request.args.get('key')
    if key is None:
        abort(400, 'Missing "key" URL parameter.')

    file_url = storage.get_image_url(key)
    if file_url is None:
        abort(400, 'No matching file found.')

    return redirect(file_url)


def download_video():
    """
    This function expects a :code:`key` URL parameter. Key is the post's ID and corresponds to the
    filename w/o extension in Storage. This endpoint should redirect to the file's location in Storage.

    :return:
        Redirects to the file's location in Storage.
    """
    key = request.args.get('key')
    if key is None:
        abort(400, 'Missing "key" URL parameter.')

    file_url = storage.get_video_url(key)
    if file_url is None:
        abort(400, 'No matching file found.')

    return redirect(file_url)


def setup_routing(app: Flask):
    """
    Basic routing function for flask.

    :param flask.Flask app: Your flask application object.
    """
    app.add_url_rule('/download/image', endpoint='download.image',
                     view_func=download_image,
                     methods=["GET"])
    app.add_url_rule('/download/video', endpoint='download.video',
                     view_func=download_video,
                     methods=["GET"])
