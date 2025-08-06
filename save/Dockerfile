FROM python:3.9.23

# base location for application source code
WORKDIR /app

# copy requirements and install them using pip
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# copy everything else the current folder has on a different docker stage
COPY templates .
COPY config.yaml .
COPY uwsgi.ini .

# Expose the http port
ARG HTTP_PORT=8586
ENV HTTP_PORT=$HTTP_PORT
EXPOSE $HTTP_PORT

# Expose the socket port
ARG SOCKET_PORT=8283
ENV SOCKET_PORT=$SOCKET_PORT
EXPOSE $SOCKET_PORT

# Startup uwsgi
CMD ["uwsgi", "--ini", "uwsgi.ini"]
