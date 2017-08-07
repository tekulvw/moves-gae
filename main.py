from flask import Flask
from raven.contrib.flask import Sentry
import logging
import os

import images

app = Flask(__name__)


def set_env_vars(app):
    app.config['PROJECT_ID'] = os.environ.get('PROJECT_ID')
    app.config['IMAGE_STORE'] = os.environ.get('IMAGE_STORE')


def maybe_setup_sentry(app):
    Sentry(app)


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


set_env_vars(app)
maybe_setup_sentry(app)

images.setup_routing(app)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
