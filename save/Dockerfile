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
COPY templates .
COPY config.yaml .
COPY uwsgi.ini .
COPY --from=pywb_arquivo . pywb_arquivo/

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
