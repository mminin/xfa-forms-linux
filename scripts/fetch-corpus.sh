#!/bin/sh
# Downloads the forms listed in corpus/forms.tsv into corpus/files/ and checks
# them against the tested versions. The forms belong to the Government of
# Canada and are not redistributed here.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$ROOT/corpus/files"
tail -n +2 "$ROOT/corpus/forms.tsv" | while IFS="$(printf '\t')" read -r file dept title page url sha kind needs; do
    out="$ROOT/corpus/files/$file"
    if ! curl -fsSL -o "$out" "$url"; then
        echo "FAILED  $file  ($url)"
        continue
    fi
    if echo "$sha  $out" | sha256sum -c --quiet 2>/dev/null; then
        echo "ok      $file"
    else
        echo "CHANGED $file  (differs from the tested version)"
    fi
done
