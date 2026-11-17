#!/usr/bin/env bash
# Moves and resizes the window whose title contains TITLE, through a one-shot KWin script
# (KDE Plasma 5, X11). Used by the docs recording scripts to lay out Gazebo, RViz and terminals.
#
#   kwin_place.sh TITLE X Y WIDTH HEIGHT       e.g. kwin_place.sh "Gazebo Sim" 2560 0 1280 1440
set -euo pipefail
[ $# -eq 5 ] || { echo "usage: $0 TITLE X Y WIDTH HEIGHT" >&2; exit 2; }
title=$1 x=$2 y=$3 w=$4 h=$5
name="jo_sim_place_$$"
js=$(mktemp --suffix=.js)
trap 'rm -f "$js"; qdbus org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript "$name" >/dev/null 2>&1 || true' EXIT
# The title goes in through JSON.parse of a quoted string, so quotes in it can't break the script
quoted=$(python3 -c 'import json,sys; print(json.dumps(json.dumps(sys.argv[1])))' "$title")
cat > "$js" <<EOF
const title = JSON.parse($quoted);
for (const c of workspace.clientList()) {
    if (c.caption.indexOf(title) >= 0 && c.normalWindow) {
        c.setMaximize(false, false);
        c.frameGeometry = {x: $x, y: $y, width: $w, height: $h};
        workspace.activeClient = c;
    }
}
EOF
qdbus org.kde.KWin /Scripting org.kde.kwin.Scripting.loadScript "$js" "$name" >/dev/null
qdbus org.kde.KWin /Scripting org.kde.kwin.Scripting.start >/dev/null
sleep 0.5
