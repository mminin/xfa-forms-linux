#!/bin/sh
# Downloads the forms listed in corpus/forms.tsv into corpus/files/ and checks
# them against the tested versions. The forms belong to the Government of
# Canada and are not redistributed here.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$ROOT/corpus/files"
download=
trap 'rm -f "$download"' EXIT
failures=0
{
read -r header
while IFS="$(printf '\t')" read -r file dept title page url sha kind needs; do
    out="$ROOT/corpus/files/$file"
    if [ -f "$out" ] && printf '%s  %s\n' "$sha" "$out" | sha256sum -c --quiet 2>/dev/null; then
        echo "cached  $file"
        continue
    fi
    download=$(mktemp "$out.XXXXXX")
    if ! curl -fsSL -o "$download" "$url"; then
        echo "FAILED  $file  ($url)"
        rm -f "$download"
        failures=$((failures + 1))
        continue
    fi
    if printf '%s  %s\n' "$sha" "$download" | sha256sum -c --quiet 2>/dev/null; then
        mv "$download" "$out"
        echo "ok      $file"
    else
        echo "CHANGED $file  (differs from the tested version; download discarded)"
        rm -f "$download"
        failures=$((failures + 1))
    fi
done
} < "$ROOT/corpus/forms.tsv"
if [ "$failures" -gt 0 ]; then
    echo "$failures corpus downloads failed verification" >&2
    exit 1
fi
