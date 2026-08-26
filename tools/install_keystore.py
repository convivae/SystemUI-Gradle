#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""install_keystore.py — Convert AOSP platform.pk8 + platform.x509.pem into a
PKCS12 keystore suitable for AGP ``signingConfig``.

Replaces the historical ``tools/install_keystore.sh`` (ADR 0002 .sh→.py
conversion, task 067). The openssl/keytool command chain is logically
equivalent to the shell script; only the orchestration is Python.

Recipe from: ``<aosp-root>/build/target/product/security/README``

Produces (in ``--dest``, default ``<project>/keystore``):
  ``<key-name>.keystore``   (PKCS12 via keytool, password=android)

Idempotent: re-running overwrites outputs. Intermediate files
(``<key-name>.p12``, ``<key-name>.key.pem``, ``<key-name>.crt.pem``) are
created and removed; only the ``.keystore`` is kept.

AOSP root resolution honours the single-source rule (user, 2026-08-25):
``--aosp-root`` > ``AOSP_ROOT`` env > ``aosp_paths.DEFAULT_AOSP_ROOT``.

SYSOPS: The AOSP platform key is a development test key bundled with AOSP.
NEVER use it to sign packages for production releases.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from aosp_paths import aosp_root

# Script lives in tools/; keystore/ is the project sibling (matches the .sh's
# ``SCRIPT_DIR/../keystore``).
_TOOLS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TOOLS_DIR.parent
_DEFAULT_DEST = _PROJECT_ROOT / "keystore"
_DEFAULT_KEY_NAME = "platform"
_STORE_PASSWORD = "android"
_KEY_ALIAS = "AndroidDebugKey"


def security_dir(aosp: Path | str | None = None) -> Path:
    """AOSP platform test-key directory under the resolved AOSP root."""
    return aosp_root(aosp) / "build" / "target" / "product" / "security"


def build_command_chain(
    src_pk8: Path,
    key_pem: Path,
    crt_pem: Path,
    p12: Path,
    keystore: Path,
) -> list[list[str]]:
    """Return the ordered openssl/keytool command list (no ``cp``).

    Factored out so tests can verify the command sequence without invoking
    openssl/keytool. Step 2 (``cp``) is handled separately via
    :func:`shutil.copyfile` since it is not part of the openssl/keytool chain.
    """
    return [
        # Step 1: pk8 (DER private key) → PEM private key
        [
            "openssl", "pkcs8", "-inform", "DER", "-nocrypt",
            "-in", str(src_pk8), "-out", str(key_pem),
        ],
        # Step 3: PEM key + PEM cert → PKCS12
        [
            "openssl", "pkcs12", "-export",
            "-in", str(crt_pem), "-inkey", str(key_pem),
            "-out", str(p12),
            "-password", f"pass:{_STORE_PASSWORD}",
            "-name", _KEY_ALIAS,
        ],
        # Step 4: import PKCS12 into keystore (keytool -importkeystore)
        [
            "keytool", "-importkeystore",
            "-deststorepass", _STORE_PASSWORD,
            "-destkeystore", str(keystore),
            "-srckeystore", str(p12),
            "-srcstoretype", "PKCS12",
            "-srcstorepass", _STORE_PASSWORD,
        ],
    ]


def generate(
    aosp: Path | str | None = None,
    key_name: str = _DEFAULT_KEY_NAME,
    dest: Path | str = _DEFAULT_DEST,
) -> Path:
    """Generate ``<dest>/<key-name>.keystore`` from the AOSP platform key.

    Raises ``FileNotFoundError`` if the AOSP ``.pk8``/``.x509.pem`` inputs are
    missing. Returns the path to the generated keystore.
    """
    sec = security_dir(aosp)
    src_pk8 = sec / f"{key_name}.pk8"
    src_pem = sec / f"{key_name}.x509.pem"
    for f in (src_pk8, src_pem):
        if not f.is_file():
            raise FileNotFoundError(f"AOSP security input not found: {f}")

    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    key_pem = dest / f"{key_name}.key.pem"
    crt_pem = dest / f"{key_name}.crt.pem"
    p12 = dest / f"{key_name}.p12"
    keystore = dest / f"{key_name}.keystore"

    # Step 2 (cp): x509.pem is already PEM; copy so naming is consistent.
    # Must precede step 3 (openssl pkcs12 -in crt_pem).
    shutil.copyfile(src_pem, crt_pem)

    # Step 1: pk8 (DER) → PEM private key
    # Step 3: PEM key + PEM cert → PKCS12
    # Step 4: PKCS12 → JKS keystore
    for cmd in build_command_chain(src_pk8, key_pem, crt_pem, p12, keystore):
        subprocess.run(cmd, check=True)

    # Cleanup intermediates (keep only the JKS keystore). Matches .sh `rm -f`.
    for f in (key_pem, crt_pem, p12):
        try:
            f.unlink()
        except FileNotFoundError:
            pass

    return keystore


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert AOSP platform.pk8 + platform.x509.pem into a JKS keystore "
            "for AGP signingConfig (replaces install_keystore.sh)."
        ),
    )
    parser.add_argument(
        "--aosp-root",
        default=None,
        help="AOSP checkout root (default: aosp_paths resolution — AOSP_ROOT env "
             "or /home/conv/myspace/aosp).",
    )
    parser.add_argument(
        "--key-name",
        default=_DEFAULT_KEY_NAME,
        help=f"Platform key basename (default: {_DEFAULT_KEY_NAME!r}).",
    )
    parser.add_argument(
        "--dest",
        default=str(_DEFAULT_DEST),
        help=f"Output directory (default: {_DEFAULT_DEST}).",
    )
    args = parser.parse_args(argv)

    keystore = generate(args.aosp_root, args.key_name, args.dest)
    size = keystore.stat().st_size
    print(f"Keystore generated: {keystore} ({size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
