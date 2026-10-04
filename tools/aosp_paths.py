"""Single source of truth for AOSP tree locations used by ``tools/`` scripts.

Every script under ``tools/`` must resolve AOSP paths through this module
instead of hardcoding absolute paths (user rule, 2026-08-25). Use an explicit
``--aosp-root`` or ``AOSP_ROOT`` for a checkout outside the repository's sibling
``aosp`` directory; no user name or OS-specific home layout is assumed.

Precedence: explicit ``override`` argument (e.g. a ``--aosp-root`` CLI value)
> ``AOSP_ROOT`` environment variable > ``DEFAULT_AOSP_ROOT``.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Optional checkout convention, relative to this repository (not the cwd).
# Callers report missing inputs rather than silently selecting another tree.
DEFAULT_AOSP_ROOT = PROJECT_ROOT.parent / "aosp"

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
