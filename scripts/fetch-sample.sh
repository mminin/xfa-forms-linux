#!/bin/sh
# Downloads the form this work was tested with from the Government of Canada
# and checks that it is the tested version.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
URL=https://travel.gc.ca/travel-voyage/assets/child/consent-letter-2123.pdf
SHA256=7ca5d486fcb69ea6d5dbfa11f6bebff3fc323d1931be91dd7052a04ba09fd2d1
OUT="$ROOT/samples/consent-letter-2123.pdf"
mkdir -p "$ROOT/samples"
if [ -f "$OUT" ] && printf '%s  %s\n' "$SHA256" "$OUT" | sha256sum -c --quiet 2>/dev/null; then
    echo "cached $OUT (tested version)"
    exit 0
fi
download=$(mktemp "$OUT.XXXXXX")
trap 'rm -f "$download"' EXIT
curl -fsSL -o "$download" "$URL"
if ! printf '%s  %s\n' "$SHA256" "$download" | sha256sum -c --quiet; then
    echo "download differs from the tested version; discarded without replacing $OUT" >&2
    exit 1
fi
mv "$download" "$OUT"
echo "saved $OUT (tested version)"
