#!/usr/bin/env bash
# Convert AOSP platform.pk8 + platform.x509.pem into a PKCS12 keystore
# suitable for AGP signingConfig.
#
# Recipe from:
#   /home/conv/myspace/aosp/build/target/product/security/README
#
# Produces:
#   keystore/platform.p12         (PKCS12, password=android)
#   keystore/platform.keystore    (JKS via keytool, password=android)
#
# Idempotent: re-running overwrites outputs.
#
# SYSOPS: The AOSP platform key is a development test key bundled with
# AOSP. NEVER use it to sign packages for production releases.
set -euo pipefail

AOSP_SEC="${AOSP_SECURITY:-/home/conv/myspace/aosp/build/target/product/security}"
KEY_NAME="${KEY_NAME:-platform}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$SCRIPT_DIR/../keystore"
mkdir -p "$DEST"

PK8="$AOSP_SEC/${KEY_NAME}.pk8"
PEM="$AOSP_SEC/${KEY_NAME}.x509.pem"

for f in "$PK8" "$PEM"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: $f not found." >&2
        exit 1
    fi
done

P12="$DEST/${KEY_NAME}.p12"
KEYSTORE="$DEST/${KEY_NAME}.keystore"
KEY_PEM="$DEST/${KEY_NAME}.key.pem"
CRT_PEM="$DEST/${KEY_NAME}.crt.pem"

# Step 1: pk8 (DER private key) → PEM private key
openssl pkcs8 -inform DER -nocrypt -in "$PK8" -out "$KEY_PEM"

# Step 2: x509.pem is already PEM; copy so naming is consistent
cp -f "$PEM" "$CRT_PEM"

# Step 3: PEM key + PEM cert → PKCS12
openssl pkcs12 -export \
    -in "$CRT_PEM" \
    -inkey "$KEY_PEM" \
    -out "$P12" \
    -password pass:android \
    -name AndroidDebugKey

# Step 4: PKCS12 → JKS keystore (keytool accepts PKCS12 src)
keytool -importkeystore \
    -deststorepass android \
    -destkeystore "$KEYSTORE" \
    -srckeystore "$P12" \
    -srcstoretype PKCS12 \
    -srcstorepass android

# Cleanup intermediates (keep only the JKS)
rm -f "$KEY_PEM" "$CRT_PEM" "$P12"

echo "Keystore generated:"
ls -lh "$KEYSTORE"