FROM python:3.12-slim
# run as an unprivileged user: a bug in the gateway can't touch the rest of the container
RUN useradd --system --no-create-home gateway && mkdir /data && chown gateway /data
# pypdf: the only extra package, for reading PDF documents in knowledge sources
RUN pip install --no-cache-dir pypdf==6.14.2
WORKDIR /app
COPY gateway.py sources.py security.py mcp.py seed_demo.py admin.html admin.js chat.html chat.js docs.html style.css ui.js docs.js logo.svg ./
COPY fonts ./fonts
USER gateway
EXPOSE 8080
CMD ["python", "-u", "gateway.py"]
