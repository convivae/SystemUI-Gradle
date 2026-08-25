"""Single source of truth for AOSP tree locations used by ``tools/`` scripts.

Every script under ``tools/`` must resolve AOSP paths through this module
instead of hardcoding absolute paths (user rule, 2026-08-25). Moving the
checkout is a one-line change here -- or a per-invocation ``AOSP_ROOT``
environment override -- never a per-script edit.

Precedence: explicit ``override`` argument (e.g. a ``--aosp-root`` CLI value)
> ``AOSP_ROOT`` environment variable > ``DEFAULT_AOSP_ROOT``.
"""
from __future__ import annotations

import os
from pathlib import Path

# Default AOSP checkout location on the build machine.
DEFAULT_AOSP_ROOT = Path("/home/conv/myspace/aosp")

# Environment variable honoured by every helper in this module.
AOSP_ROOT_ENV = "AOSP_ROOT"


def aosp_root(override: Path | str | None = None) -> Path:
    """Resolve the AOSP tree root (see module docstring for precedence)."""
    if override is not None:
        return Path(override).expanduser()
    env_value = os.environ.get(AOSP_ROOT_ENV)
    if env_value:
        return Path(env_value).expanduser()
    return DEFAULT_AOSP_ROOT


def soong_intermediates(override: Path | str | None = None) -> Path:
    """``out/soong/.intermediates`` under the resolved AOSP root."""
    return aosp_root(override) / "out" / "soong" / ".intermediates"
