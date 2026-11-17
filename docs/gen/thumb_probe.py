"""Runs INSIDE the jo_sim container (fed on stdin by docs/gen/gen_world_catalogue.py).

For each world given on the command line (name, or name@azimuth,elevation,zoom to override the view):
prepare the world as the launch does and run it headless WITHOUT the robot; frame it from a nadir
depth image (the extent of whatever stands more than 0.4 m above the ground, or of the terrain,
trimmed of outliers),
then render a 3/4 view (azimuth 225°: from the south-west; elevation 50°) at the distance that fits
that extent. Saves /tmp/jo_sim/thumbs/<world>.jpg and prints one JSON line per world.
ROS_DOMAIN_ID and GZ_PARTITION come from the caller.
"""
import json, math, os, signal, subprocess, sys, threading, time

import xml.etree.ElementTree as ET

import yaml
import numpy as np
from jo_sim.world_tools import (_is_placeholder_datum, prepare_world, resolve_world, resource_dirs,
                              world_settings)

OUT = '/tmp/jo_sim/thumbs'
SETTLE_S = float(os.environ.get('THUMB_SETTLE', '12'))
AZ, EL, ZOOM = 225.0, 50.0, 1.0   # default view: from the south-west, 50° down; zoom > 1: closer
W, H = 1280, 720                  # render size; saved at 800x450
NADIR_Z, NADIR_FOV, NADIR_PX = 300.0, 1.4, 600
MAX_EXTENT = 600.0                # [m] cap for worlds whose content never ends
MAX_Z = 1200.0                    # [m] highest nadir pass


def sensor_sdf(name, kind, w, h, fov, far):
    return f'''<sdf version="1.9"><model name="{name}"><static>true</static><link name="link">
<sensor name="s" type="{kind}"><always_on>true</always_on><update_rate>5</update_rate><topic>/thumb/{name}</topic>
<camera><horizontal_fov>{fov}</horizontal_fov><image><width>{w}</width><height>{h}</height>
{'<anti_aliasing>4</anti_aliasing>' if kind == 'camera' else ''}</image><clip><near>0.1</near><far>{far}</far></clip></camera>
</sensor></link></model></sdf>'''


class Gz:
    """The few gz-transport calls the probe needs (spawn, move, step, read one image)."""

    def __init__(self, world):
        from gz.transport13 import Node
        self.node, self.world, self.cv, self.imgs = Node(), world, threading.Condition(), {}

    def call(self, service, req, rep_type, timeout=5000):
        ok, rep = self.node.request(f'/world/{self.world}/{service}', req, type(req), rep_type, timeout)
        return ok and getattr(rep, 'data', True)

    def spawn(self, name, sdf, xyz, rpy):
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.entity_factory_pb2 import EntityFactory
        from gz.msgs10.image_pb2 import Image
        req = EntityFactory()
        req.sdf, req.name = sdf, name
        self._pose(req.pose, xyz, rpy)
        if not self.call('create', req, Boolean):
            raise RuntimeError(f'spawn {name} failed')
        self.node.subscribe(Image, f'/thumb/{name}', lambda m, n=name: self._on_img(n, m))

    def move(self, name, xyz, rpy):
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.pose_pb2 import Pose
        p = Pose()
        p.name = name
        self._pose(p, xyz, rpy)
        self.call('set_pose', p, Boolean)

    @staticmethod
    def _pose(p, xyz, rpy):
        r, pi, y = (a / 2 for a in rpy)
        p.position.x, p.position.y, p.position.z = xyz
        p.orientation.w = math.cos(r) * math.cos(pi) * math.cos(y) + math.sin(r) * math.sin(pi) * math.sin(y)
        p.orientation.x = math.sin(r) * math.cos(pi) * math.cos(y) - math.cos(r) * math.sin(pi) * math.sin(y)
        p.orientation.y = math.cos(r) * math.sin(pi) * math.cos(y) + math.sin(r) * math.cos(pi) * math.sin(y)
        p.orientation.z = math.cos(r) * math.cos(pi) * math.sin(y) - math.sin(r) * math.sin(pi) * math.cos(y)

    def _on_img(self, name, m):
        with self.cv:
            self.imgs[name] = m
            self.cv.notify_all()

    def image(self, name, steps=400, timeout=30):
        """Steps the world (so the pose change applies and the sensor renders) and returns a new image."""
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.world_control_pb2 import WorldControl
        with self.cv:
            self.imgs.pop(name, None)
        req = WorldControl()
        req.pause, req.multi_step = True, steps
        self.call('control', req, Boolean)
        end = time.time() + timeout
        with self.cv:
            while name not in self.imgs:
                if not self.cv.wait(max(0.0, end - time.time())):
                    raise TimeoutError(f'no image from {name}')
            return self.imgs[name]


def look_rpy(eye, target):
    dx, dy, dz = (t - e for t, e in zip(target, eye))
    return 0.0, math.atan2(-dz, math.hypot(dx, dy)), math.atan2(dy, dx)


def content_box(depth, z_cam, fov, cx, cy):
    """World (x0, y0, x1, y1, ground z, touches the image edge) of the content of a nadir depth image:
    whatever is more than 0.4 m above the ground (the far, common surface), or all of a terrain.
    Trimmed of the outermost 1 % on each side, so a lone far object does not stretch the frame."""
    n = depth.shape[1]
    d = np.where(np.isfinite(depth) & (depth > 0), depth, np.nan)
    if np.all(np.isnan(d)):
        return None
    ground = np.nanpercentile(d, 90)
    mask = d < ground - 0.4
    if mask.sum() < 20:
        return None
    if os.environ.get('THUMB_DEBUG'):
        from PIL import Image
        Image.fromarray((mask * 255).astype(np.uint8)).save(f'{OUT}/debug_{int(z_cam)}.png')
    rows, cols = np.nonzero(mask)
    m_px = 2 * ground * math.tan(fov / 2) / n               # metres per pixel at the ground
    # image top = +x when looking down with yaw 0 (pitch +90 deg); image right = -y
    c0, c1 = np.percentile(cols, [1, 99])
    r0, r1 = np.percentile(rows, [1, 99])
    edge = min(c0, r0) < 3 or max(c1, r1) > n - 4
    xs = cx + (n / 2 - np.array([r1, r0])) * m_px
    ys = cy - (np.array([c0, c1]) - n / 2) * m_px
    top = float(ground - np.nanpercentile(d[mask], 1))     # height of the tallest content
    return float(xs[0]), float(min(ys)), float(xs[1]), float(max(ys)), float(z_cam - ground), edge, top


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
    az, el, zoom = (float(v) for v in view.split(',')) if view else (AZ, EL, ZOOM)
    path = resolve_world(world)
    st = world_settings(path, {}, '')
    info = meta(world, path, st)
    if os.environ.get('THUMB_META_ONLY'):
        return info
    patched, _ = prepare_world(path, st['latitude'], st['longitude'], st['elevation'])
    env = dict(os.environ)
    env['GZ_SIM_RESOURCE_PATH'] = ':'.join([*resource_dirs(path), env.get('GZ_SIM_RESOURCE_PATH', '')])
    with open(f'/tmp/jo_sim/thumb_{world}.log', 'w') as log:
        proc = subprocess.Popen(['gz', 'sim', '-s', '--headless-rendering', '-v', '1', patched],
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=env)
    try:
        wname = None
        for _ in range(int(SETTLE_S * 4)):
            out = subprocess.run(['gz', 'service', '-l'], capture_output=True, text=True).stdout
            wname = next((l.split('/')[2] for l in out.splitlines()
                          if l.startswith('/world/') and l.endswith('/control')), None)
            if wname:
                break
            if proc.poll() is not None:
                return {**info, 'error': 'gz sim died'}
            time.sleep(0.25)
        if not wname:
            return {**info, 'error': 'no world'}
        time.sleep(SETTLE_S)  # meshes and textures load in the background
        gz = Gz(wname)
        sx, sy = float(st['x']), float(st['y'])
        spawn = (sx, sy)
        # 1. nadir depth: the extent of the content (a second, closer pass when it is small)
        gz.spawn('nadir', sensor_sdf('nadir', 'depth_camera', NADIR_PX, NADIR_PX, NADIR_FOV, 5000),
                 (sx, sy, NADIR_Z), (0, math.pi / 2, 0))
        box, z = None, NADIR_Z
        for _ in range(6):
            gz.move('nadir', (sx, sy, z), (0, math.pi / 2, 0))
            m = gz.image('nadir')
            depth = np.frombuffer(m.data, dtype=np.float32).reshape(m.height, m.width)
            found = content_box(depth, z, NADIR_FOV, sx, sy)
            if not found:
                if box or z <= 20:
                    break
                z = 60.0 if z > 60 else 15.0  # small content: look again from lower down
                continue
            box = found
            ext = max(box[2] - box[0], box[3] - box[1])
            if box[5] and z < MAX_Z:          # cut by the image edge: look again from higher up
                sx, sy, z = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, min(MAX_Z, 2 * z)
                continue
            want = max(30.0, 1.3 * ext / (2 * math.tan(NADIR_FOV / 2)) + box[4])
            if want > 0.6 * z:                # already sharp enough
                break
            sx, sy, z = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, want
        if box:
            cx, cy, gz_ = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, box[4]
            ext = min(MAX_EXTENT, max(12.0, math.hypot(box[2] - box[0], box[3] - box[1]) + 0.8 * box[6]))
        else:
            cx, cy, gz_, ext = sx, sy, float(st['z']), 30.0
        # 2. the 3/4 view: distance that fits the extent (diagonal) in the horizontal field of view
        fov = 1.0
        dist = max(6.0, 0.62 * ext / math.tan(fov / 2)) / zoom
        a, e = math.radians(az), math.radians(el)
        eye = (cx + dist * math.cos(e) * math.cos(a), cy + dist * math.cos(e) * math.sin(a),
               gz_ + dist * math.sin(e))
        target = (cx, cy, gz_)
        gz.spawn('view', sensor_sdf('view', 'camera', W, H, fov, max(2000, 3 * dist)), eye, look_rpy(eye, target))
        gz.image('view')                       # the first image can be dark while the scene loads
        time.sleep(2)
        m = gz.image('view')
        from PIL import Image
        os.makedirs(OUT, exist_ok=True)
        img = Image.frombytes('RGB', (m.width, m.height), m.data)
        img.resize((800, 450), Image.LANCZOS).save(f'{OUT}/{world}.jpg', quality=84)
        return {**info, 'thumb': f'{OUT}/{world}.jpg',
                'view': {'center': [round(cx, 1), round(cy, 1)], 'extent': round(ext, 1),
                         'distance': round(dist, 1), 'az': az, 'el': el}}
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(20)
            except subprocess.TimeoutExpired:
                pass
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        time.sleep(2)


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
