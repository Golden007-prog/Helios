# Helios backend image — Code Engine target.
#
# Build with the *repo root* as context so we can pull in the shared corpus
# the runtime reads (abend patterns, review-queue policy, parser gap log):
#   docker build -t helios-backend:local -f backend/Dockerfile .
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
COPY backend/pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip \
 && pip install -e .

# Source.
COPY backend/app /app/app
COPY backend/migrations /app/migrations

# Runtime corpus the backend reads:
#   - shared/sample-corpus/abend_patterns/patterns.yaml  (abend classifier)
#   - shared/config/review_queue_defaults.yaml           (review policy)
# The parser gap log at /app/docs/PARSER_GAPS.md is created on-demand by
# the runtime; we just need the parent dir to exist + be writable.
COPY shared /app/shared
RUN mkdir -p /app/docs

# Build metadata — set by CI via --build-arg.
ARG HELIOS_GIT_SHA=unknown
ARG HELIOS_BUILD_TIME=unknown
ARG HELIOS_IMAGE_TAG=unknown
ENV HELIOS_GIT_SHA=${HELIOS_GIT_SHA} \
    HELIOS_BUILD_TIME=${HELIOS_BUILD_TIME} \
    HELIOS_IMAGE_TAG=${HELIOS_IMAGE_TAG}

# Non-root user. The /app/docs path needs to be writable so the gap logger
# can flush at shutdown (PARSER_GAPS.md is mostly read-only at runtime, but
# the logger appends if a parser surfaces something new).
RUN useradd -m -u 1001 helios \
 && chown -R helios:helios /app/docs
USER helios

EXPOSE 8080

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips=*"]
