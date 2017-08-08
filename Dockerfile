FROM gcr.io/google_appengine/python
RUN apt-get -y update && apt-get install -y libav-tools

RUN virtualenv /env -p python3.5

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

ADD requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

ADD . /app

CMD gunicorn -k gevent --timeout 60 -b :$PORT main:app