#!/bin/sh
# Run the locally built evince against the locally built poppler.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PREFIX="$ROOT/_install"
# GTK's default preview command starts `evince --preview`, which in turn starts
# `evince-previewer`. Both must come from this build, just like the backend.
export PATH="$PREFIX/bin:$PATH"
export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
export XDG_DATA_DIRS="$PREFIX/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export GSETTINGS_SCHEMA_DIR="$PREFIX/share/glib-2.0/schemas"
export EV_BACKENDS_DIR="$(ls -d "$PREFIX"/lib*/evince/*/backends "$PREFIX"/lib/*/evince/*/backends 2>/dev/null | head -1)"
exec "$PREFIX/bin/evince" "$@"
