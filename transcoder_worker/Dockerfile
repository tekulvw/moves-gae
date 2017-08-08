FROM gcr.io/google_appengine/python

RUN apt-get -y update && apt-get install -y libav-tools


# Create a virtualenv for dependencies. This isolates these packages from
 # system-level packages.
RUN virtualenv /env

 # Setting these environment variables are the same as running
 # source /env/bin/activate.
ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

 # Copy the application's requirements.txt and run pip to install all
 # dependencies into the virtualenv.
ADD requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# # Add the application source code.
ADD . /app

CMD honcho start -f /app/procfile worker monitor