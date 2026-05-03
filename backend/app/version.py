"""Build / version metadata exposed via /version.

Populated at container build time via env vars. Falls back to the package
__version__ + ``unknown`` when not set, which is the case during local dev.
"""

from __future__ import annotations

import os

from app import __version__


def build_info() -> dict[str, str]:
    return {
        "version": __version__,
        "git_sha": os.environ.get("HELIOS_GIT_SHA", "unknown"),
        "build_time": os.environ.get("HELIOS_BUILD_TIME", "unknown"),
        "image_tag": os.environ.get("HELIOS_IMAGE_TAG", "unknown"),
    }
