# Helios backend image — Code Engine target.
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# OS deps. tini gives us a real init for signal handling on Code Engine.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Python deps first for layer caching.
COPY pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip \
 && pip install -e .

# Source.
COPY app /app/app
COPY migrations /app/migrations

# Build metadata — set by CI via --build-arg.
ARG HELIOS_GIT_SHA=unknown
ARG HELIOS_BUILD_TIME=unknown
ARG HELIOS_IMAGE_TAG=unknown
ENV HELIOS_GIT_SHA=${HELIOS_GIT_SHA} \
    HELIOS_BUILD_TIME=${HELIOS_BUILD_TIME} \
    HELIOS_IMAGE_TAG=${HELIOS_IMAGE_TAG}

# Non-root user.
RUN useradd -m -u 1001 helios
USER helios

EXPOSE 8080

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips=*"]
