# python:3.12-slim, pinned by digest so every build starts from the same bytes (Dependabot proposes updates).
FROM python:3.12-slim@sha256:02108f5d322dd89f1c9e552442c25acb0543dfdbc455693a5599624f20d9155d

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Run as an unprivileged user: a bug in the gateway can't touch the rest of the container.
# /data holds everything the gateway writes: the database, its key file, backups.
RUN useradd --system --no-create-home gateway && mkdir /data && chown gateway /data && chmod 700 /data

# Exact versions + hashes; prebuilt wheels only, so no compiler is ever needed or left in the image.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes --only-binary :all: -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Code stays owned by root: the gateway user can read it but not change it.
WORKDIR /app
COPY gateway.py settings.py sources.py security.py mcp.py seed_demo.py \
     admin.html admin.js chat.html chat.js docs.html docs.js style.css ui.js logo.svg \
     i18n.js en-admin.js en-chat.js en-docs.js ./
COPY fonts ./fonts

USER gateway
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '8080'), timeout=4)"]
CMD ["python", "-u", "gateway.py"]
