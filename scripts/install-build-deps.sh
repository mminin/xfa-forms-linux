#!/bin/sh
# Build dependencies for upstream/poppler (master) and upstream/evince (main, GTK4)
# on Ubuntu 24.04. Run once: sudo sh scripts/install-build-deps.sh
set -e

apt-get update
apt-get install -y \
    build-essential cmake ninja-build meson pkg-config git python3-venv \
    itstool gettext desktop-file-utils appstream \
    libfreetype-dev libfontconfig-dev libcairo2-dev libglib2.0-dev \
    libgirepository1.0-dev gobject-introspection \
    libopenjp2-7-dev liblcms2-dev libnss3-dev libjpeg-dev libpng-dev libtiff-dev \
    libgpgmepp-dev libgpgme-dev libboost-dev libcurl4-openssl-dev libbrotli-dev \
    libharfbuzz-dev zlib1g-dev \
    libgtk-4-dev libadwaita-1-dev libsecret-1-dev libexempi-dev \
    libspectre-dev libsynctex-dev libarchive-dev libdjvulibre-dev libgxps-dev \
    libgnome-desktop-4-dev libgdk-pixbuf-2.0-dev libdbus-1-dev \
    gsettings-desktop-schemas libsysprof-capture-4-dev \
    libgtk-3-dev  # poppler's glib tests still link GTK3

# Ubuntu 24.04 has no QuickJS package; the XFA scripting milestone vendors it instead.
echo "done"
