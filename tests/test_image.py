from flask import url_for


def test_image_upload_bad_data(test_client):
    with test_client.application.app_context():
        resp = test_client.post(
            url_for('image'),
            data=dict(),
            follow_redirects=True
        )

    assert resp.status_code == 400
