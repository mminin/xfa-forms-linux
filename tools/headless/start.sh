#!/bin/sh
# Headless GNOME Shell + rootful Xwayland :77 for driving Evince.
H=$(cd "$(dirname "$0")" && pwd)
export XDG_CONFIG_HOME=$H/config XDG_DATA_HOME=$H/data XDG_CACHE_HOME=$H/cache GSETTINGS_BACKEND=memory
unset DISPLAY WAYLAND_DISPLAY
export PATH=$H/bin:$PATH
gnome-shell --mode=user --headless --wayland --no-x11 --wayland-display=wl-xfa --virtual-monitor 1400x1000 > $H/shell.log 2>&1 &
for i in $(seq 50); do [ -S "$XDG_RUNTIME_DIR/wl-xfa" ] && break; sleep 0.2; done
WAYLAND_DISPLAY=wl-xfa Xwayland :77 -shm -nolisten tcp -geometry 1400x1000 -fullscreen > $H/xwayland.log 2>&1 &
echo "$DBUS_SESSION_BUS_ADDRESS" > $H/bus
wait
