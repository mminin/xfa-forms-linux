#!/bin/sh
# Runs the patched Evince on :77 with the headless session's bus.
H=$(cd "$(dirname "$0")" && pwd)
R=$(cd "$H/../.." && pwd)
P=$R/_install
export GTK_IM_MODULE=simple DBUS_SESSION_BUS_ADDRESS=$(cat $H/bus) DISPLAY=:77 GDK_BACKEND=x11 GSETTINGS_BACKEND=memory
export XDG_CONFIG_HOME=$H/config XDG_DATA_HOME=$H/data XDG_CACHE_HOME=$H/cache
unset WAYLAND_DISPLAY
export LD_LIBRARY_PATH=$P/lib/x86_64-linux-gnu:$P/lib XDG_DATA_DIRS=$P/share:/usr/share
export GSETTINGS_SCHEMA_DIR=$P/share/glib-2.0/schemas EV_BACKENDS_DIR=$P/lib/x86_64-linux-gnu/evince/6/backends
exec gdb -q -batch -ex run -ex bt -ex "thread apply all bt 8" --args $P/bin/evince "$@"
