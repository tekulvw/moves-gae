from pathlib import Path

from google.cloud.storage import Client

client = Client()


def upload_file(data: str, content_type: str, full_path: Path) -> str:
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

    bucket_name, blob_parts = full_path.parts[0], full_path.parts[1:]
    blob_path = Path(*blob_parts)

    bucket = client.bucket(bucket_name=bucket_name)
    blob = bucket.blob(str(blob_path))

    blob.upload_from_string(data, content_type=content_type)
    blob.make_public()

    return blob.public_url
