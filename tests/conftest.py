import pytest


@pytest.fixture()
def app():
    from main import app
    app.testing = True
    app.config['SERVER_NAME'] = 'localhost'
    return app


@pytest.fixture()
def test_client(app):
    with app.test_client() as c:
        yield c

