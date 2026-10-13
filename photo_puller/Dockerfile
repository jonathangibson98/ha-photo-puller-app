ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-requests

COPY main.py ui.html /

CMD ["python3", "-u", "/main.py"]
