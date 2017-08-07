from io import BytesIO

import flask
from PIL import Image, ExifTags
from flask import request, abort
from werkzeug.datastructures import FileStorage

from storage import upload_image, generate_image_path


def image_upload():
    """
    Endpoint for just image upload.

    Expects form data fields "output", "ext" and "content-type" which are used
    to save the output name. Expects image to be uploaded as multipart/file-upload
    and accessible under the name "image".
    :return:
    """
    image, output, ext, content_type = _extract_base_image_form_data()
    _handle_image_uploading(image.read(), output, ext, content_type)
    return '', 204


def _extract_base_image_form_data():
    """
    Extracts form data for :py:function:`image_upload`.
    :return:
        Necessary form elements
    :rtype:tuple
    """
    form = request.form
    output = form.get('output')
    ext = form.get('ext')
    content_type = form.get('content-type')
    image = request.files.get('image')

    if None in (output, ext, image, content_type):
        abort(400, 'Missing required data field. See documentation for more details')

    return image, output, ext, content_type


def _handle_image_uploading(image: BytesIO, output: str, ext: str, content_type: str) -> str:
    """
    Uploads the given image to Cloud Storage at the location specified by environment
    variable "IMAGE_STORE".

    :param BytesIO image:
    :param output:
        Output filename, appended to base location.
    :param ext:
        Extension for the given image.
    :return:
        Full path location in Cloud Storage
    """

    full_path = generate_image_path(output, ext)

    return upload_image(image, content_type, full_path)


def image_upload_with_overlay():
    """
    Endpoint for image + overlay upload.
    :return:
    """
    overlay, (image, output, ext, content_type) = _extract_overlay_form_data()

    combined_image = _combine_images(image, overlay, ext)

    _handle_image_uploading(combined_image, output, ext, content_type)
    return '', 204


def _combine_images(background: FileStorage, overlay: FileStorage,
                    ext: str) -> BytesIO:
    """
    Combines a background image and overlay using PIL.
    :param background:
    :param overlay:
    :param ext:
    :return:
        Object ready for uploading.
    :rtype:BytesIO
    """
    background = _check_rotation_exif(Image.open(background))
    overlay = _check_rotation_exif(Image.open(overlay))

    background = background.convert("RGBA")
    overlay = overlay.convert("RGBA")

    overlay = overlay.resize(background.size)

    background.paste(
        overlay,
        (0, 0, background.size[0], background.size[1]),
        overlay
    )

    background = background.convert("RGB")

    data = BytesIO()

    try:
        background.save(data, format=ext)
    except KeyError as e:
        abort(400, str(e))

    data.seek(0)

    return data


def _check_rotation_exif(image: Image) -> Image:
    """
    Checks the rotational exif data on a given image and rotates it
    accordingly.
    :param image:
    :return:
        Rotated image.
    :rtype:
        PIL.Image
    """
    for orientation in ExifTags.TAGS.keys():
        if ExifTags.TAGS[orientation] == 'Orientation':
            try:
                exif = dict(image._getexif().items())
            except AttributeError:
                return image

            if exif[orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image = image.rotate(90, expand=True)
            return image
    return image


def _extract_overlay_form_data():
    """
    Extracts all data required for :py:function:`image_upload_with_overlay`.
    :rtype:tuple
    """
    overlay = request.files.get('overlay')

    if overlay is None:
        abort(400, 'Missing overlay upload.')

    return overlay, _extract_base_image_form_data()


def setup_routing(app: flask.Flask):
    app.add_url_rule('/image_upload', endpoint='image',
                     view_func=image_upload,
                     methods=["POST"])
    app.add_url_rule('/image_upload_with_overlay', endpoint='image.overlay',
                     view_func=image_upload_with_overlay,
                     methods=["POST"])
