#!/bin/sh
# Stops the harness Evince (matched by its executable, never the system one).
E=$(cd "$(dirname "$0")/../.." && pwd)/_install/bin/evince
for p in $(pgrep -f "_install/bin/evince"); do
    case "$(readlink /proc/$p/exe 2>/dev/null)" in "$E"|"$E (deleted)") kill $p;; esac
done
sleep 1
