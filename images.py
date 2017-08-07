from pathlib import Path

import flask
from flask import request, abort, current_app
from werkzeug.datastructures import FileStorage

from storage import upload_file


def image_upload():
    """
    Endpoint for just image upload.

    Expects form data fields "output", "ext" and "content-type" which are used
    to save the output name. Expects image to be uploaded as multipart/file-upload
    and accessible under the name "image".
    :return:
    """
    form = request.form
    output = form.get('output')
    ext = form.get('ext')
    content_type = form.get('content-type')
    image = request.files.get('image')

    if None in (output, ext, image, content_type):
        abort(400, 'Missing required data field. See documentation for more details')

    # Now that we have something for each field...

    _handle_image_uploading(image, output, ext, content_type)
    return '', 204


def _handle_image_uploading(image: FileStorage, output: str, ext: str, content_type: str) -> str:
    """
    Uploads the given image to Cloud Storage at the location specified by environment
    variable "IMAGE_STORE".

    :param werkzeug.datastructures.FileStorage image:
        Object direct from a :code:`request.files` MultiDict/upload.
    :param output:
        Output filename, appended to base location.
    :param ext:
        Extension for the given image.
    :return:
        Full path location in Cloud Storage
    """
    data = image.stream.read()

    full_path = _generate_storage_path(output, ext)

    return upload_file(data, content_type, full_path)


def _generate_storage_path(output_name: str, ext: str) -> Path:
    """
    Generates the full path to be passed to :py:function:`storage.upload_file`.
    :param output_name:
        Output filename, usually gathered from an upload request.
    :param ext:
        Output extension, usually gathered from an upload request.
    :return:
        Full path to be passed to :py:function:`storage.upload_file`.
    """
    image_store = current_app.config['IMAGE_STORE']

    path = "{}/{}.{}".format(image_store, output_name, ext)

    return Path(path)


def image_upload_with_overlay():
    """
    Endpoint for image + overlay upload.
    :return:
    """
    pass


def setup_routing(app: flask.Flask):
    app.add_url_rule('/image_upload', endpoint='image',
                     view_func=image_upload,
                     methods=["POST"])
    app.add_url_rule('/image_upload_with_overlay', endpoint='image.overlay',
                     view_func=image_upload_with_overlay,
                     methods=["POST"])
