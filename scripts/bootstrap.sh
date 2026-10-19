#!/bin/sh
# Fetches each upstream project listed in UPSTREAM at its base commit into
# upstream/<name> and applies patches/<name>/*.patch on a branch xfa-support.
# Run it once after cloning, then scripts/build.sh.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
while read -r name url base; do
    case "$name" in ''|\#*) continue ;; esac
    dir="$ROOT/upstream/$name"
    fingerprint=$({
        printf '%s\n' "$base"
        if [ -d "$ROOT/patches/$name" ]; then
            (cd "$ROOT/patches/$name" && for patch in *.patch; do
                [ -f "$patch" ] || continue
                sha256sum "$patch"
            done)
        fi
    } | sha256sum | cut -d ' ' -f 1)
    if [ ! -e "$dir/.git" ]; then
        git init -q "$dir"
    fi
    pending_am=$(git -C "$dir" rev-parse --path-format=absolute --git-path rebase-apply)
    if [ -d "$pending_am" ]; then
        echo "upstream/$name has an unfinished git am; resolve it or abort it before retrying" >&2
        exit 1
    fi
    complete=$(git -C "$dir" config --get xfa.bootstrap-source || true)
    applied=$(git -C "$dir" config --get xfa.bootstrap-head || true)
    if [ "$complete" = "$fingerprint" ] && [ -n "$applied" ] &&
       git -C "$dir" merge-base --is-ancestor "$applied" HEAD; then
        echo "upstream/$name already bootstrapped; preserving local edits"
        continue
    fi
    pending=$(git -C "$dir" config --get xfa.bootstrap-pending || true)
    head=$(git -C "$dir" rev-parse --verify HEAD 2>/dev/null || true)
    if [ -n "$head" ] && { [ "$pending" != "$fingerprint" ] || [ "$head" != "$base" ]; }; then
        echo "upstream/$name does not match a completed bootstrap of these patches" >&2
        echo "Keep any local work and use a fresh checkout to apply the current package" >&2
        exit 1
    fi
    if [ -n "$(git -C "$dir" status --porcelain)" ]; then
        echo "upstream/$name has local changes in an unfinished bootstrap; preserve them before retrying" >&2
        exit 1
    fi
    git -C "$dir" config xfa.bootstrap-pending "$fingerprint"
    if git -C "$dir" remote get-url origin >/dev/null 2>&1; then
        git -C "$dir" remote set-url origin "$url"
    else
        git -C "$dir" remote add origin "$url"
    fi
    if [ -z "$head" ]; then
        git -C "$dir" fetch -q --depth 1 origin "$base"
        git -C "$dir" checkout -q -b xfa-support FETCH_HEAD
    fi
    set -- "$ROOT"/patches/"$name"/*.patch
    if [ -f "$1" ]; then
        # git am needs a committer; fall back to a neutral one if none is set
        git -C "$dir" -c user.name="${GIT_COMMITTER_NAME:-$(git config user.name || echo builder)}" \
            -c user.email="${GIT_COMMITTER_EMAIL:-$(git config user.email || echo builder@localhost)}" \
            am -q --committer-date-is-author-date "$@"
    fi
    git -C "$dir" config xfa.bootstrap-head "$(git -C "$dir" rev-parse HEAD)"
    git -C "$dir" config xfa.bootstrap-source "$fingerprint"
    git -C "$dir" config --unset xfa.bootstrap-pending
    echo "upstream/$name: $(git -C "$dir" log --oneline | wc -l) commits on $base"
done < "$ROOT/UPSTREAM"
