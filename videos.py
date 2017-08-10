"""
List of Endpoints
=================

    - :code:`/upload/video`: Handled by :py:func:`video_upload`.
    - :code:`/upload/video/overlay`: Handled by :py:func:`video_upload_with_overlay`.

API Reference
=============
"""

import json
import logging
from flask import Flask, request, abort, current_app
from werkzeug.datastructures import FileStorage
from google.cloud import pubsub

import storage

log = logging.getLogger(__name__)


# Now based on:
#  https://github.com/waprin/appengine-transcoder


def video_upload():
    """
    This requires "post_id", "ext" and "content-type" as form data keys along with
    "video" file key (also form data technically).

    :return:
        - 204 - No content.
        - 400 - Missing data field.
        - 5XX - Request too large.
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


def video_upload_with_overlay():
    """
    Video upload with an overlay image. This endpoint will schedule transcoding
    of the video (e.g. it won't happen in this request call).

    Requires an extra "overlay" form data field that must be a PNG.

    :return:
        - 204 - No content.
        - 400 - Missing data field.
        - 5XX - Request too large.
    """
    overlay, (video, file_name, ext, content_type) = _extract_overlay_data()

    _publish_video_overlay_upload(overlay, video, file_name, ext, content_type)

    return '', 204


def _publish_video_overlay_upload(overlay: FileStorage, video: FileStorage,
                                  file_name: str, ext: str, content_type: str):
    """
    Uploads overlay and video to Cloud storage for later transcoding and publishes
    to Cloud PubSub.
    :param overlay:
    :param video:
    :param str file_name:
    :param str ext:
    :param str content_type:
    :return:
    """
    path = storage.generate_transcoding_path()

    overlay_path = path / 'overlay.png'
    video_path = path / (file_name + '.' + ext)

    storage.upload_data(overlay, 'image/png', overlay_path)
    storage.upload_data(video, content_type, video_path)

    pubsub_payload = dict(
        video=str(video_path),
        overlay=str(overlay_path),
        content_type=content_type
    )

    topic = _get_transcode_topic()
    topic.publish(json.dumps(pubsub_payload).encode('utf-8'))


def _get_transcode_topic():
    client = pubsub.Client(
        project=current_app.config['PROJECT_ID'],
        _use_grpc=False
    )
    topic = client.topic(current_app.config['TRANSCODE_TOPIC'])
    return topic


def _extract_overlay_data():
    """
    Extracts overlay data from form data.
    :return:
    """
    normal_data = _extract_data_video_upload()
    overlay = request.files.get('overlay')
    if overlay is None:
        abort(400, 'Missing overlay file.')

    return overlay, normal_data


def setup_routing(app: Flask):
    """
    Basic routing function for flask.

    :param flask.Flask app: Your flask application object.
    """
    app.add_url_rule('/upload/video', endpoint='video',
                     view_func=video_upload,
                     methods=["POST"])
    app.add_url_rule('/upload/video/overlay', endpoint='video.overlay',
                     view_func=video_upload_with_overlay,
                     methods=["POST"])
