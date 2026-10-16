#!/bin/sh
# Starts a private headless GNOME Shell with a rootful Xwayland on :77 (no
# IBus, settings in memory). Then: ./evince.sh file.pdf, and drive it with
# python drive.py click X Y | type TEXT | key ctrl+s | shot out.png (needs
# python-xlib and Pillow). ./stop.sh stops the harness Evince.
H=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$H/data/dbus-1/services" "$H/config" "$H/cache"
for n in org.freedesktop.IBus org.freedesktop.portal.IBus; do
    printf '[D-BUS Service]\nName=%s\nExec=%s/bin/ibus-daemon\n' $n "$H" > "$H/data/dbus-1/services/$n.service"
done
XDG_DATA_HOME=$H/data exec dbus-run-session -- "$H/start.sh"
