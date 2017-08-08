from io import BytesIO
from pathlib import Path
from typing import Union

from flask import current_app
from google.cloud import storage


def _get_storage_client():
    return storage.Client(
        project=current_app.config['PROJECT_ID']
    )


def _get_bucket() -> storage.Bucket:
    client = _get_storage_client()
    image_store = current_app.config['STORAGE_BUCKET']
    return client.bucket(image_store)


def _get_image_prefix() -> str:
    return current_app.config['IMAGE_PREFIX']


def _get_video_prefix() -> str:
    return current_app.config['VIDEO_PREFIX']


def generate_image_path(output_name: str, ext: str) -> Path:
    """
    Generates the full path to be passed to :py:function:`upload_file`.
    :param output_name:
        Output filename, usually gathered from an upload request.
    :param ext:
        Output extension, usually gathered from an upload request.
    :return:
        Full path to be passed to :py:function:`upload_file`.
    """
    image_store = _get_image_prefix()

    path = "{}/{}.{}".format(image_store, output_name, ext)

    return Path(path)


def generate_video_path(output_name: str, ext: str) -> Path:
    """
    Generates the full path to be passed to :py:function:`upload_file`.
    :param output_name:
        Output filename, usually gathered from an upload request.
    :param ext:
        Output extension, usually gathered from an upload request.
    :return:
        Full path to be passed to :py:function:`storage.upload_file`.
    """
    video_store = _get_video_prefix()
    path = "{}/{}.{}".format(video_store, output_name, ext)

    return Path(path)


def upload_data(data: BytesIO, content_type: str, full_path: Path) -> str:
    """
    Uploads binary data to the given path on Google Cloud Storage.
    :param data:
        Binary data (for now just photos/videos).
    :param content_type:
        Correct content type for the data we're uploading.
    :param full_path:
        Full path including bucket.
    :raises ValueError:
        If :code:`full_path` begins with a leading slash.
    :return:
        Public URL to access file.
    """
    if full_path.is_absolute():
        raise ValueError("full_path may not start with a leading slash.")

    bucket = _get_bucket()
    blob = bucket.blob(str(full_path))

    blob.upload_from_string(data.read(), content_type=content_type)
    blob.make_public()

    return blob.public_url


def get_public_url(filename: str) -> Union[str, None]:
    """
    Get's a files public url based on the filename. Could be a video or image.
    :param filename:
    :return: Public URL
    """
    url = get_image_url(filename)
    if url is None:
        url = get_video_url(filename)

    return url


def get_image_url(filename: str) -> Union[str, None]:
    """
    Gets an image's public url based on the filename without extension.
    :param filename:
    :return:
    """
    bucket = _get_bucket()
    img_prefix = _get_image_prefix()

    for blob in bucket.list_blobs(prefix=img_prefix):
        path = Path(blob.name)
        if path.stem == filename:
            return blob.public_url


def get_video_url(filename: str) -> Union[str, None]:
    """
    Gets a video's public url based on the filename without extension.
    :param filename:
    :return:
    """
    bucket = _get_bucket()
    vid_prefix = _get_video_prefix()

    for blob in bucket.list_blobs(prefix=vid_prefix):
        path = Path(blob.name)
        if path.stem == filename:
            return blob.public_url

