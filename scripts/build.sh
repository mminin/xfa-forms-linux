#!/bin/sh
# Build upstream/poppler and upstream/evince into ./_install (nothing touches the system).
# Then run the patched viewer with: scripts/run-evince.sh samples/consent-letter-2123.pdf
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PREFIX="$ROOT/_install"

# QuickJS runs the scripts of XFA forms; static, linked into libpoppler.
cmake -S "$ROOT/upstream/quickjs" -B "$ROOT/_build/quickjs" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_SHARED_LIBS=OFF
ninja -C "$ROOT/_build/quickjs" install

cmake -S "$ROOT/upstream/poppler" -B "$ROOT/_build/poppler" -G Ninja \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_PREFIX_PATH="$PREFIX" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_RPATH="$PREFIX/lib" \
    -DENABLE_QT5=OFF -DENABLE_QT6=OFF -DENABLE_GTK_DOC=OFF -DENABLE_GPGME=OFF \
    -DENABLE_UNSTABLE_API_ABI_HEADERS=ON -DBUILD_GTK_TESTS=ON
ninja -C "$ROOT/_build/poppler" install

export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH"
export LD_LIBRARY_PATH="$PREFIX/lib:$PREFIX/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

if [ ! -d "$ROOT/_build/evince" ]; then
    meson setup "$ROOT/_build/evince" "$ROOT/upstream/evince" --prefix="$PREFIX" \
        -Dprofile=devel -Dnautilus=false -Dintrospection=false -Dgtk_doc=false -Duser_doc=false \
        -Dps=disabled -Ddjvu=disabled -Ddvi=disabled -Dxps=disabled -Dcomics=disabled -Dtiff=disabled
fi
ninja -C "$ROOT/_build/evince" install
echo "built into $PREFIX"
