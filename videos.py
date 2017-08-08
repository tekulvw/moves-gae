import json
import logging
from flask import Flask, request, abort, current_app
from werkzeug.datastructures import FileStorage
from google.cloud import pubsub

import storage

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


def video_upload_with_overlay():
    overlay, (video, file_name, ext, content_type) = _extract_overlay_data()

    _publish_video_overlay_upload(overlay, video, file_name, ext, content_type)

    return '', 204


def _publish_video_overlay_upload(overlay: FileStorage, video: FileStorage,
                                  file_name: str, ext: str, content_type: str):
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
        project=current_app.config['PROJECT_ID']
    )
    topic = client.topic(current_app.config['TRANSCODE_TOPIC'])
    if not topic.exists():
        topic.create()
    return topic


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
