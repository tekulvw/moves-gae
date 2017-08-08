from io import BytesIO
from subprocess import getoutput, run, PIPE

import os
from PIL import Image


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