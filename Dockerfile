FROM gcr.io/google_appengine/python
RUN apt-get -y update && apt-get install -y libav-tools