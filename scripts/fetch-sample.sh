#!/bin/sh
# Downloads the form this work was tested with from the Government of Canada
# and checks that it is the tested version.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
URL=https://travel.gc.ca/travel-voyage/assets/child/consent-letter-2123.pdf
SHA256=7ca5d486fcb69ea6d5dbfa11f6bebff3fc323d1931be91dd7052a04ba09fd2d1
OUT="$ROOT/samples/consent-letter-2123.pdf"
mkdir -p "$ROOT/samples"
curl -fsSL -o "$OUT" "$URL"
if echo "$SHA256  $OUT" | sha256sum -c --quiet; then
    echo "saved $OUT (tested version)"
else
    echo "warning: $OUT differs from the tested version; the form may have been updated" >&2
fi
