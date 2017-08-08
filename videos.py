from io import BytesIO
from pathlib import Path
from subprocess import getoutput, run
import logging
import os
from PIL import Image
from flask import Flask, request, abort

import storage
import images

log = logging.getLogger(__name__)


# I thoroughly dislike doing this, here's the alternative:
# https://github.com/waprin/appengine-transcoder


def video_upload():
    """
    This requires "post_id", "ext" and "content-type" as form data keys along with
    "video" file key (also form data technically).
    :return:
    """
    video, file_name, ext, content_type = _extract_data_video_upload()

    full_path = storage.generate_video_path(file_name, ext)

    storage.upload_data(video, content_type, full_path)
    return '', 204


def _extract_data_video_upload():
    """
    Extracts required data from form data for video uploading.
    :return:
    """
    video = request.files.get('video')
    file_name = request.form.get('post_id')
    ext = request.form.get('ext')
    content_type = request.form.get('content-type')

    if None in (video, file_name, ext, content_type):
        abort(400, 'Missing required data field.')

    return video, file_name, ext, content_type


def _get_resolution(video: BytesIO) -> (int, int):
    """
    Gets the resolution of a video by saving it to a file and using avprobe.
    :param video:
    :return: width, height
    """
    import uuid
    tmploc = "/tmp/{}".format(uuid.uuid4())

    video.seek(0)
    with open(tmploc, mode='wb') as f:
        f.write(video.read())
    video.seek(0)

    cmd = ("/usr/bin/avconv -i " + tmploc + r" 2>&1 | perl -lane 'print $1 if /(\d{2,10}x\d{2,10})/'")

    output = getoutput(cmd)

    # Expected output:
    # width=1280
    # height=720

    # width_line, height_line = output.split('\n')[:2]

    # _, width = width_line.split('=')
    # _, height = height_line.split('=')

    width, height = output.split('x')

    return int(width), int(height)


def _render_overlay(video: BytesIO, overlay: Image) -> BytesIO:
    """
    Renders an image onto a video, will also resize the overlay to match
    video resolution.
    :param video:
    :param overlay:
    :return: New video.
    """
    size = _get_resolution(video)

    # noinspection PyProtectedMember
    overlay = images._check_rotation_exif(overlay)
    overlay = overlay.resize(size)

    import uuid

    tmp_loc = "/tmp/{}.mp4".format(uuid.uuid4())
    overlay_loc = "/tmp/{}.png".format(uuid.uuid4())
    output_loc = "/tmp/{}.mp4".format(uuid.uuid4())

    overlay.save(overlay_loc, "PNG")

    with open(tmp_loc, 'wb') as f:
        f.write(video.read())
        video.seek(0)

    cmd = ["/usr/bin/avconv", "-i", tmp_loc, "-i", overlay_loc, "-strict", "-2",
           "-filter_complex", '"overlay=0:0"', output_loc]

    output = run(cmd)
    if output.returncode != 0:
        raise RuntimeError("Avconv process did not return successfully. LOG:\n"
                           "{}\n\n{}".format(output.stdout, output.stderr))

    with open(output_loc, 'rb') as f:
        output = BytesIO(f.read())

    os.remove(tmp_loc)
    os.remove(overlay_loc)
    os.remove(output_loc)

    return output


def video_upload_with_overlay():
    overlay, (video, file_name, ext, content_type) = _extract_overlay_data()

    overlay = Image.open(overlay)

    new_vid = _render_overlay(video, overlay)
    full_path = storage.generate_video_path(file_name, ext)

    storage.upload_data(new_vid, content_type, full_path)
    return '', 204


def _extract_overlay_data():
    normal_data = _extract_data_video_upload()
    overlay = request.files.get('overlay')
    if overlay is None:
        abort(400, 'Missing overlay file.')

    return overlay, normal_data


def setup_routing(app: Flask):
    app.add_url_rule('/video_upload', endpoint='video',
                     view_func=video_upload,
                     methods=["POST"])
    app.add_url_rule('/video_upload_with_overlay', endpoint='video.overlay',
                     view_func=video_upload_with_overlay,
                     methods=["POST"])
