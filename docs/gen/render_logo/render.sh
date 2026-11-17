#!/usr/bin/env bash
# Renders the site logo, favicon and home-page render (docs/assets/images/jo_logo.png, favicon.png,
# jo_render.png) from the URDF.
# CPU only: Blender Cycles on the CPU, with CUDA hidden. Needs the jo_sim container running (for
# xacro), Blender on the host, and python3 with numpy and Pillow.
# Usage: docs/gen/render_logo/render.sh [azimuth_deg] [elevation_deg]   (default -40 25: front-right)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd); repo=$(cd "$here/../../.." && pwd)
az=${1:--40}; el=${2:-25}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
docker exec jo_sim-jo-sim-1 bash -c 'source /opt/ros/jazzy/setup.bash; source /home/ros/install/setup.bash;
  xacro /home/ros/src/jo_description/urdf/jo_main.urdf.xacro sim_noise:=false' > "$tmp/jo.urdf"
python3 "$here/urdf2json.py" "$tmp/jo.urdf" "$repo/jo_description/meshes" "$tmp/scene.json"
CUDA_VISIBLE_DEVICES="" __NV_PRIME_RENDER_OFFLOAD=0 nice -n 10 \
  blender -b --factory-startup -noaudio -P "$here/render_jo.py" -- "$tmp/scene.json" "$tmp/jo.png" 512 "$az" "$el"
python3 - "$tmp/jo.png" "$repo/docs/assets/images" <<'PY'
import sys
from PIL import Image
im = Image.open(sys.argv[1]); im = im.crop(im.getbbox())
s = max(im.size); sq = Image.new('RGBA', (s, s), (0, 0, 0, 0)); sq.paste(im, ((s - im.width) // 2, (s - im.height) // 2))
sq.resize((256, 256), Image.LANCZOS).save(sys.argv[2] + '/jo_logo.png', optimize=True)
sq.resize((64, 64), Image.LANCZOS).save(sys.argv[2] + '/favicon.png', optimize=True)
sq.resize((440, 440), Image.LANCZOS).save(sys.argv[2] + "/jo_render.png", optimize=True)
PY
echo "written: docs/assets/images/jo_logo.png, favicon.png, jo_render.png"
