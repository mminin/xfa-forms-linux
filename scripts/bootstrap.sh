#!/bin/sh
# Fetches each upstream project listed in UPSTREAM at its base commit into
# upstream/<name> and applies patches/<name>/*.patch on a branch xfa-support.
# Run it once after cloning, then scripts/build.sh.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
grep -v '^#' "$ROOT/UPSTREAM" | while read -r name url base; do
    [ -n "$name" ] || continue
    dir="$ROOT/upstream/$name"
    if [ -d "$dir/.git" ]; then
        echo "upstream/$name exists, leaving it alone"
        continue
    fi
    git init -q "$dir"
    git -C "$dir" remote add origin "$url"
    git -C "$dir" fetch -q --depth 1 origin "$base"
    git -C "$dir" checkout -q -b xfa-support FETCH_HEAD
    if [ -d "$ROOT/patches/$name" ]; then
        # git am needs a committer; fall back to a neutral one if none is set
        git -C "$dir" -c user.name="${GIT_COMMITTER_NAME:-$(git config user.name || echo builder)}" \
            -c user.email="${GIT_COMMITTER_EMAIL:-$(git config user.email || echo builder@localhost)}" \
            am -q --committer-date-is-author-date "$ROOT"/patches/"$name"/*.patch
    fi
    echo "upstream/$name: $(git -C "$dir" log --oneline | wc -l) commits on $base"
done
