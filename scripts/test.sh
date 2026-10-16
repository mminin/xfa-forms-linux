#!/bin/sh
# Runs the synthetic poppler tests (built here directly, so GTK 3 headers are
# not needed) and, when the sample form is present, the end-to-end scenario.
# Run after scripts/build.sh.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PREFIX="$ROOT/_install"
OUT="$ROOT/_work/tests"
mkdir -p "$OUT"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH"
for t in check_form_type check_xfa; do
    cc -o "$OUT/$t" "$ROOT/upstream/poppler/glib/tests/$t.c" \
        $(pkg-config --cflags --libs poppler-glib gio-2.0) -Wl,-rpath,"$PREFIX/lib"
    (cd "$OUT" && ./"$t")
done

FORM=${FORM:-$ROOT/samples/consent-letter-2123.pdf}
if [ -f "$FORM" ]; then
    FORM="$FORM" "$ROOT/tools/consent-letter-scenario.sh" "$OUT/scenario.pdf" > "$OUT/scenario.log" 2>&1
    pdftotext "$OUT/scenario.pdf" - | grep -q "Alex Example" && echo "ok scenario: letter generated ($OUT/scenario.pdf)"
else
    echo "skip scenario: put the form at samples/consent-letter-2123.pdf (see README)"
fi
