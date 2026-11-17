"""Runs INSIDE the jo_sim container (fed on stdin by docs/gen/gen_world_catalogue.py).

For each world given on the command line: launch launch_sim headless with the sensors off, spawn a
static camera behind and above Jo's spawn pose, let Gazebo save its frames (<save> in the camera
SDF), and keep the last one as /tmp/jo_sim/thumbs/<world>.jpg. Prints one JSON line per world.
ROS_DOMAIN_ID and GZ_PARTITION come from the caller.
"""
import glob, json, math, os, shutil, signal, subprocess, sys, time

import xml.etree.ElementTree as ET

import yaml
from jo_sim.world_tools import _is_placeholder_datum, resolve_world, sidecar_path, world_settings

OUT = '/tmp/jo_sim/thumbs'
SETTLE_S = float(os.environ.get('THUMB_SETTLE', '20'))
BACK, UP = 7.0, 4.0  # default camera offset from the spawn pose [m]; per world: name@back,up
W, H = 960, 540

CAMERA = '''<sdf version="1.9"><model name="thumb_cam"><static>true</static><link name="link">
<sensor name="thumb" type="camera"><always_on>true</always_on><update_rate>2</update_rate><topic>thumb_cam</topic>
<camera><horizontal_fov>1.2</horizontal_fov><image><width>{w}</width><height>{h}</height></image>
<clip><near>0.1</near><far>500</far></clip><save enabled="true"><path>{path}</path></save></camera>
</sensor></link></model></sdf>'''


def meta(world, path, st):
    """What the catalogue shows besides the picture: description, datum and its source, spawns."""
    side = {}
    if st['sidecar']:
        side = yaml.safe_load(open(st['sidecar'])) or {}
    sc = ET.parse(path).getroot().find('world/spherical_coordinates')
    if sc is not None and not _is_placeholder_datum(sc):
        datum = ('world', float(sc.findtext('latitude_deg')), float(sc.findtext('longitude_deg')))
    elif side.get('gnss'):
        datum = ('sidecar', st['latitude'], st['longitude'])
    else:
        datum = ('default', st['latitude'], st['longitude'])
    return {'world': world, 'description': st['description'], 'datum': datum,
            'spawn': [st[k] for k in ('x', 'y', 'z', 'yaw')], 'spawns': sorted(side.get('spawns') or {})}


def shoot(arg):
    world, _, view = arg.partition('@')
    back, up = (float(v) for v in view.split(',')) if view else (BACK, UP)
    path = resolve_world(world)
    st = world_settings(path, {}, '')
    info = meta(world, path, st)
    if os.environ.get('THUMB_META_ONLY'):
        return info
    frames = f'/tmp/jo_sim/thumb_frames/{world}'
    shutil.rmtree(frames, ignore_errors=True)
    os.makedirs(frames)
    cmd = ['ros2', 'launch', 'jo_sim', 'launch_sim.launch.py', f'world:={world}', 'gui:=false',
           'follow:=false', 'gz_verbosity:=1', 'lidar:=false', 'imu:=false', 'gnss:=false',
           'front_cam:=false', 'back_cam:=false']
    with open(f'/tmp/jo_sim/thumb_{world}.log', 'w') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        time.sleep(SETTLE_S)
        if proc.poll() is not None:
            return {**info, 'error': 'launch died'}
        x, y, z, yaw = (float(st[k]) for k in ('x', 'y', 'z', 'yaw'))
        cx, cy, cz = x - back * math.cos(yaw), y - back * math.sin(yaw), z + up
        pitch = math.atan2(up, back)  # positive pitch looks down
        subprocess.run(['ros2', 'run', 'ros_gz_sim', 'create', '-name', 'thumb_cam',
                        '-string', CAMERA.format(w=W, h=H, path=frames),
                        '-x', str(cx), '-y', str(cy), '-z', str(cz), '-P', str(pitch), '-Y', str(yaw)],
                       capture_output=True, timeout=30)
        # Gazebo renders a camera only while something subscribes to it: <save> alone writes nothing
        sub = subprocess.Popen(['gz', 'topic', '-e', '-t', '/thumb_cam'], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        t0 = time.time()
        while time.time() - t0 < 40 and len(glob.glob(f'{frames}/*.png')) < 4:
            time.sleep(1)  # the first frames can be dark while the scene loads
        sub.kill()
        # the newest frame may still be being written: take the one before it
        shots = sorted(glob.glob(f'{frames}/*.png'), key=os.path.getmtime)[:-1]
        if not shots:
            return {**info, 'error': 'no frame saved'}
        from PIL import Image
        os.makedirs(OUT, exist_ok=True)
        Image.open(shots[-1]).convert('RGB').resize((640, 360)).save(f'{OUT}/{world}.jpg', quality=82)
        return {**info, 'thumb': f'{OUT}/{world}.jpg'}
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(30)
            except subprocess.TimeoutExpired:
                pass
        # ros2 launch can exit while gz sim survives (seen in the thumbnail batch): kill what's left
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        shutil.rmtree(frames, ignore_errors=True)
        time.sleep(3)


def main():
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(1))
    signal.signal(signal.SIGHUP, lambda *a: sys.exit(1))
    for world in sys.argv[1:]:
        print(f'[thumb] {world}', file=sys.stderr, flush=True)
        try:
            result = shoot(world)
        except Exception as e:  # one broken world must not stop the batch
            result = {'world': world.partition('@')[0], 'error': f'{type(e).__name__}: {e}'}
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
