FROM python:3.14.8

COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /bin/

# install the dependencies locked on the repository uv.lock (uv_project build context)
# on a virtual environment outside the application folder, used by uwsgi.ini
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never
ENV VIRTUAL_ENV=/opt/venv
ENV PATH=/opt/venv/bin:$PATH

# base location for application source code
WORKDIR /app

RUN --mount=type=bind,from=uv_project,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,from=uv_project,source=uv.lock,target=uv.lock \
    uv sync --locked --no-dev --no-install-project

# copy everything else the current folder has on a different docker stage
COPY . .

# Expose the http port
ARG HTTP_PORT=8082
ENV HTTP_PORT=$HTTP_PORT
EXPOSE $HTTP_PORT

# Expose the socker port
ARG SOCKET_PORT=8484
ENV SOCKET_PORT=$SOCKET_PORT
EXPOSE $SOCKER_PORT

# Startup uwsgi
CMD ["uwsgi", "--ini", "uwsgi.ini"]
