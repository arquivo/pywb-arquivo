FROM python:3.9.23

# base location for application source code
WORKDIR /app

# copy requirements and install them using pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy everything else the current folder has on a different docker stage
COPY . .

# Expose the http port
ARG HTTP_PORT=8082
ENV HTTP_PORT $HTTP_PORT
EXPOSE $HTTP_PORT

# Expose the socker port
ARG SOCKER_PORT=8484
ENV SOCKER_PORT $SOCKER_PORT
EXPOSE $SOCKER_PORT

# Startup uwsgi
CMD ["uwsgi", "--ini", "uwsgi.ini"]
