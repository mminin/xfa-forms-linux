#!/bin/sh
# Run on the private tools/headless desktop. No physical print jobs are sent.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PREFIX="$ROOT/_install"
OUT="$ROOT/_work/tests"
mkdir -p "$OUT"
export PATH="$PREFIX/bin:$PATH"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib/x86_64-linux-gnu/pkgconfig:${PKG_CONFIG_PATH:-}"
export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export XDG_DATA_DIRS="$PREFIX/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export EV_BACKENDS_DIR="$PREFIX/lib/x86_64-linux-gnu/evince/6/backends"
export GSETTINGS_SCHEMA_DIR="$PREFIX/share/glib-2.0/schemas"
export GSETTINGS_BACKEND=memory GTK_IM_MODULE=simple
cc -Wall -Wextra -Werror -Wno-unused-parameter -Wno-deprecated-declarations \
    -o "$OUT/check-printing" "$ROOT/tools/headless/check-printing.c" \
    $(pkg-config --cflags --libs evince-view-4.0 evince-document-4.0 gtk4-unix-print)
exec python3 "$ROOT/tools/qa/test_printing.py" "$@"
