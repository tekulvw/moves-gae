import json
from io import BytesIO
from pathlib import Path
from subprocess import getoutput, run, PIPE
import base64

from google.cloud import storage, pubsub

import os
from PIL import Image, ExifTags


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
    overlay = _check_rotation_exif(overlay)
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
           "-codec:v", "libx264", "-b:v", "2048k", "-bufsize", "500k", "-filter_complex",
           "overlay=0:0", output_loc]

    output = run(cmd, stdout=PIPE, stderr=PIPE)
    if output.returncode != 0:
        raise RuntimeError("Avconv process did not return successfully. LOG:\n"
                           "{}\n\n{}".format(output.stdout, output.stderr))

    with open(output_loc, 'rb') as f:
        output = BytesIO(f.read())

    os.remove(tmp_loc)
    os.remove(overlay_loc)
    os.remove(output_loc)

    return output


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


def get_from_storage(path, proj, buckname) -> BytesIO:
    client = storage.Client(project=proj)
    bucket = client.bucket(buckname)

    blob = bucket.get_blob(path)

    return BytesIO(blob.download_as_string())


def _upload_final(video: BytesIO, file_name, proj, bucket, content_type):
    client = storage.Client(project=proj)
    bucket = client.bucket(bucket)

    video_prefix = os.environ.get('VIDEO_PREFIX')

    file_path = Path(video_prefix, file_name)

    blob = bucket.blob(str(file_path))

    blob.upload_from_string(video.read(), content_type=content_type)

    blob.make_public()


def process_message(msg, proj, bucket):
    data = json.loads(msg.data.decode('utf-8'))

    video_loc = data['video']
    overlay_loc = data['overlay']
    content_type = data['content_type']

    video = get_from_storage(video_loc, proj, bucket)
    overlay = Image.open(get_from_storage(overlay_loc, proj, bucket))

    output = _render_overlay(video, overlay)

    _upload_final(output, Path(video_loc).name, proj, bucket, content_type)


if __name__ == '__main__':
    project_id = os.environ.get('PROJECT_ID')
    transcode_topic_name = os.environ.get('TRANSCODE_TOPIC')
    bucket_name = os.environ.get('STORAGE_BUCKET')

    pubsub_client = pubsub.Client(project=project_id)
    topic = pubsub_client.topic(transcode_topic_name)
    if not topic.exists():
        topic.create()

    sub = topic.subscription('transcode_worker', ack_deadline=60)
    if not sub.exists():
        sub.create()

    print("Polling pubsub.")

    while True:
        messages = sub.pull(
            return_immediately=False, max_messages=1
        )
        for ack_id, message in messages:
            process_message(message, project_id, bucket_name)
            sub.acknowledge([ack_id])
