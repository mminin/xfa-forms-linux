#!/bin/sh
# Build upstream/poppler and upstream/evince into ./_install (nothing touches the system).
# Then run the patched viewer with: scripts/run-evince.sh samples/consent-letter-2123.pdf
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PREFIX="$ROOT/_install"
JOBS=${JOBS:-4}
case "$JOBS" in ''|*[!0-9]*|0*) echo "JOBS must be a positive integer without leading zeros" >&2; exit 1 ;; esac

# QuickJS runs the scripts of XFA forms; static, linked into libpoppler.
cmake -S "$ROOT/upstream/quickjs" -B "$ROOT/_build/quickjs" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_SHARED_LIBS=OFF
ninja -j "$JOBS" -C "$ROOT/_build/quickjs" install

# Zint draws the barcodes of XFA forms; static, linked into libpoppler.
cmake -S "$ROOT/upstream/zint" -B "$ROOT/_build/zint" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DZINT_SHARED=OFF -DZINT_STATIC=ON -DZINT_FRONTEND=OFF -DZINT_USE_PNG=OFF -DZINT_USE_QT=OFF \
    -DZINT_USE_GS1SE=OFF -DZINT_UNINSTALL=OFF
ninja -j "$JOBS" -C "$ROOT/_build/zint" install

cmake -S "$ROOT/upstream/poppler" -B "$ROOT/_build/poppler" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_PREFIX_PATH="$PREFIX" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_RPATH="$PREFIX/lib" \
    -DENABLE_QT5=OFF -DENABLE_QT6=OFF -DENABLE_GTK_DOC=OFF -DENABLE_GPGME=OFF \
    -DENABLE_UNSTABLE_API_ABI_HEADERS=ON -DBUILD_GTK_TESTS=ON
ninja -j "$JOBS" -C "$ROOT/_build/poppler" install

export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH"
export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

if [ ! -d "$ROOT/_build/evince" ]; then
    meson setup "$ROOT/_build/evince" "$ROOT/upstream/evince" --prefix="$PREFIX" \
        -Dprofile=devel -Dnautilus=false -Dintrospection=false -Dgtk_doc=false -Duser_doc=false \
        -Dps=disabled -Ddjvu=disabled -Ddvi=disabled -Dxps=disabled -Dcomics=disabled -Dtiff=disabled
fi
ninja -j "$JOBS" -C "$ROOT/_build/evince" install
echo "built into $PREFIX"
