#!/bin/sh
# Exports the commits on branch xfa-support of each upstream/<name> checkout,
# on top of the base commit in UPSTREAM, into patches/<name>/.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
grep -v '^#' "$ROOT/UPSTREAM" | while read -r name url base; do
    [ -n "$name" ] && [ -d "$ROOT/upstream/$name/.git" ] || continue
    [ "$(git -C "$ROOT/upstream/$name" rev-list --count "$base..xfa-support")" -gt 0 ] || continue
    rm -rf "$ROOT/patches/$name"
    git -C "$ROOT/upstream/$name" format-patch -q -N -o "$ROOT/patches/$name" "$base..xfa-support"
    echo "$name: $(ls "$ROOT/patches/$name" | wc -l) patch(es)"
done
