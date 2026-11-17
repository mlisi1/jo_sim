"""Frame-locked recording rig for the docs videos. Runs INSIDE the jo_sim container.

The simulator runs headless and paused. For each video frame the rig moves its camera(s), steps the
world by one frame period (1/FPS of sim time), waits for the camera image of that instant, and
grabs the virtual display (Xvfb, where RViz or the GLIM viewer run) at the same instant. Every frame
is therefore complete and synchronized, whatever the speed of the machine.

Usage (fed on stdin by docs/gen/media/shoot.py, with a shot script appended):

    rig = Rig('nav_local', world='office_cpr', launch=['localization:=true', ...], rviz='nav')
    rig.start(settle=40)
    cam = rig.camera('main', 1920, 1080)
    for i in range(300):
        cam.look(eye, target)
        rig.cmd_vel(0.5, 0.0)
        rig.frame()
    rig.stop()

Frames go to /tmp/jo_sim/rig/<shot>/<camera>/%05d.png and .../xvfb/%05d.png, and a frames.jsonl
with the sim time, robot pose and any values the shot logs. ROS_DOMAIN_ID, GZ_PARTITION and DISPLAY
(the Xvfb display) come from the caller.
"""
import json, math, os, shutil, signal, subprocess, sys, threading, time

import numpy as np
from PIL import Image as PILImage, ImageGrab

from gz.transport13 import Node as GzNode
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.entity_factory_pb2 import EntityFactory
from gz.msgs10.image_pb2 import Image as GzImage
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.msgs10.world_control_pb2 import WorldControl

OUT = '/tmp/jo_sim/rig'
# 25 fps: one frame (40 ms) is a whole number of physics steps for 1, 2, 4 and 5 ms steps, so the
# camera stamps fall exactly on the frame times
FPS = 25


def log(*a):
    print('[rig]', *a, file=sys.stderr, flush=True)


def quat_rpy(roll, pitch, yaw):
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return (cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy)  # w, x, y, z


def look_rpy(eye, target):
    """Roll, pitch, yaw of a Gazebo camera (looking along +X) at `eye` looking at `target`."""
    dx, dy, dz = (t - e for t, e in zip(target, eye))
    return 0.0, math.atan2(-dz, math.hypot(dx, dy)), math.atan2(dy, dx)


def smooth(t):
    """Ease in and out, t in [0, 1]."""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


class Camera:
    def __init__(self, rig, name, width, height, fov):
        self.rig, self.name, self.size = rig, name, (width, height)
        self.dir = os.path.join(rig.out, name)
        os.makedirs(self.dir, exist_ok=True)
        self.lock = threading.Condition()
        self.latest = None  # (sim time, PIL image)
        self.buffer = None  # every image, while recording a live (unpaused) stretch
        sdf = f'''<sdf version="1.9"><model name="{name}"><static>true</static><link name="link">
<sensor name="cam" type="camera"><always_on>true</always_on><update_rate>{FPS}</update_rate>
<topic>/rig/{name}</topic><camera><horizontal_fov>{fov}</horizontal_fov>
<image><width>{width}</width><height>{height}</height><anti_aliasing>4</anti_aliasing></image>
<clip><near>0.05</near><far>800</far></clip></camera></sensor></link></model></sdf>'''
        req = EntityFactory()
        req.sdf = sdf
        req.name = name
        req.pose.position.z = 50
        ok, rep = rig.gz.request(f'/world/{rig.world}/create', req, EntityFactory, Boolean, 5000)
        if not (ok and rep.data):
            raise RuntimeError(f'camera {name}: create failed')
        rig.gz.subscribe(GzImage, f'/rig/{name}', self._on_image)

    def _on_image(self, msg):
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        img = PILImage.frombytes('RGB', (msg.width, msg.height), msg.data)
        with self.lock:
            self.latest = (t, img)
            if self.buffer is not None:
                self.buffer.append((t, img))
            self.lock.notify_all()

    def pose(self, xyz, rpy):
        w, x, y, z = quat_rpy(*rpy)
        p = Pose()
        p.name = self.name
        p.position.x, p.position.y, p.position.z = xyz
        p.orientation.w, p.orientation.x, p.orientation.y, p.orientation.z = w, x, y, z
        self.rig.gz.request(f'/world/{self.rig.world}/set_pose', p, Pose, Boolean, 2000)

    def look(self, eye, target):
        self.pose(eye, look_rpy(eye, target))

    def wait(self, t_min, timeout=20.0):
        end = time.time() + timeout
        with self.lock:
            while self.latest is None or self.latest[0] < t_min - 0.5 / FPS:
                left = end - time.time()
                if left <= 0:
                    raise TimeoutError(f'camera {self.name}: no image at t={t_min:.3f}')
                self.lock.wait(left)
            return self.latest[1]


# Solid camera clouds and thicker lidar points: the 3 px points of the source configs make a speckle
# that looks noisy in a video and multiplies its size
DOCS_CLOUDS = {'Front Camera Points': {'Style': 'Flat Squares', 'Size (m)': 0.035},
               'Back Camera Points': {'Style': 'Flat Squares', 'Size (m)': 0.035},
               'Lidar': {'Size (Pixels)': 4}}


def rviz_config(name, base='sim', view=None, fixed_frame=None, set_displays=None):
    """Writes /tmp/jo_sim/rviz_docs/<name>.rviz from a docs base config (written by shoot.py).

    view: keys of 'Views/Current' (e.g. Class, Distance, Pitch, Yaw, Focal Point, Target Frame).
    set_displays: {display name: {key: value}} merged into those displays."""
    import yaml
    with open(f'/tmp/jo_sim/rviz_docs/{base}.rviz') as f:
        cfg = yaml.safe_load(f)
    vm = cfg['Visualization Manager']
    if fixed_frame:
        vm['Global Options']['Fixed Frame'] = fixed_frame
    if view:
        cur = vm['Views']['Current']
        if 'Class' in view and view['Class'] != cur.get('Class'):
            cur.clear()
            cur['Name'] = 'Current View'
        cur.update(view)
    for d in vm['Displays']:
        d.update((set_displays or {}).get(d.get('Name'), {}))
    path = f'/tmp/jo_sim/rviz_docs/{name}.rviz'
    with open(path, 'w') as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return path


class Rig:
    def __init__(self, shot, world='office_cpr', launch=(), rviz=None, xvfb_crop=None):
        self.shot, self.world_name, self.launch_args = shot, world, list(launch)
        self.rviz, self.xvfb_crop = rviz, xvfb_crop
        self.out = os.path.join(OUT, shot)
        shutil.rmtree(self.out, ignore_errors=True)
        os.makedirs(self.out)
        self.cams, self.n, self.procs, self.ros_cams, self.ros_values = [], 0, [], [], []
        self.robot = None  # (x, y, z, yaw) of the model "jo"
        self.extra = {}
        self.records = open(os.path.join(self.out, 'frames.jsonl'), 'w')

    # ── processes ──────────────────────────────────────────────────────
    def _spawn(self, cmd, logname, env=None):
        lf = open(os.path.join(self.out, logname), 'w')
        p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, start_new_session=True,
                             env=env or os.environ)
        self.procs.append(p)
        return p

    def start(self, settle=30.0, paused_settle=False, ready_log=None, ready_timeout=240.0):
        """Launches the sim and lets it run `settle` s of wall time; with ready_log, first waits
        for that text in the launch output (e.g. 'Managed nodes are active'), then settles."""
        cmd = ['ros2', 'launch', 'jo_sim', 'sim_bringup.launch.py', f'world:={self.world_name}',
               'gui:=false', 'follow:=false', 'gz_verbosity:=1', 'rviz:=false', 'sens_rviz:=false',
               'front_cam:=true', 'back_cam:=true'] + self.launch_args  # later args win
        log('launch:', ' '.join(cmd[3:]))
        self._spawn(cmd, 'launch.log')
        if self.rviz:
            self._start_rviz()
        self.gz = GzNode()
        self.world = self._find_world()
        self.gz.subscribe(Pose_V, f'/world/{self.world}/pose/info', self._on_poses)
        import rclpy
        from geometry_msgs.msg import Twist, PoseStamped
        rclpy.init()
        from rclpy.parameter import Parameter
        self.ros = rclpy.create_node('docs_rig', parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.cmd_pub = self.ros.create_publisher(Twist, '/cmd_vel', 10)
        self.goal_pub = self.ros.create_publisher(PoseStamped, '/goal_pose', 10)
        self._Twist, self._PoseStamped = Twist, PoseStamped
        self.step_s = self._physics_step()
        if ready_log:
            end = time.time() + ready_timeout
            path = os.path.join(self.out, 'launch.log')
            while ready_log not in open(path, errors='replace').read():
                if time.time() > end:
                    raise RuntimeError(f'"{ready_log}" not in the launch output after {ready_timeout} s')
                time.sleep(2)
            log(f'"{ready_log}" after {ready_timeout - (end - time.time()):.0f} s')
        log(f'world {self.world}, physics step {self.step_s * 1000:g} ms; settling {settle} s')
        time.sleep(settle)
        if self.rviz:
            if self.rviz_proc.poll() is not None:
                log('rviz died while settling, restarting')
                self._start_rviz()
            if not self.xvfb_crop:
                self.xvfb_crop = self._find_view()
        self.control(pause=True)
        time.sleep(1.0)
        t = self.sim_time()
        # cameras render on multiples of 1/FPS of sim time: put the frame boundaries on that grid
        period = 1.0 / FPS
        lead = (math.ceil(t / period - 1e-6) * period - t) % period
        if lead > 1e-6:
            self.control(steps=round(lead / self.step_s))
            time.sleep(0.5)
        self.t = self.sim_time()
        log(f'paused at t={self.t:.3f}')

    def attach(self, cmd, ready, timeout=400.0):
        """Instead of start(): run `cmd` (e.g. the scenario runner, which launches the sim itself),
        keep every line it prints with the frame number it appeared at (self.cmd_lines), and pause
        the world once a line contains `ready`."""
        import re
        self.cmd_lines, self._ready = [], threading.Event()
        lf = open(os.path.join(self.out, 'cmd.log'), 'w')
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             start_new_session=True, bufsize=1)
        self.procs.append(p)
        self.cmd_proc = p

        def reader():
            for line in p.stdout:
                lf.write(line)
                lf.flush()
                line = re.sub(r'\x1b\[[0-9;]*m', '', line.rstrip())
                self.cmd_lines.append((self.n, line))
                if ready in line:
                    self._ready.set()
        threading.Thread(target=reader, daemon=True).start()
        log('attach:', ' '.join(cmd))
        if not self._ready.wait(timeout):
            raise RuntimeError(f'no "{ready}" from {cmd[0]} within {timeout} s')
        self.gz = GzNode()
        self.world = self._find_world()
        self.gz.subscribe(Pose_V, f'/world/{self.world}/pose/info', self._on_poses)
        import rclpy
        from geometry_msgs.msg import Twist, PoseStamped
        if not rclpy.ok():
            rclpy.init()
        from rclpy.parameter import Parameter
        self.ros = rclpy.create_node('docs_rig', parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.cmd_pub = self.ros.create_publisher(Twist, '/docs_rig/unused', 10)
        self._Twist, self._PoseStamped = Twist, PoseStamped
        self.step_s = self._physics_step()
        self.sync()
        log(f'attached to {self.world} at t={self.t:.3f}')

    def save_cmd_lines(self):
        with open(os.path.join(self.out, 'cmd_lines.json'), 'w') as f:
            json.dump(self.cmd_lines, f)

    def _start_rviz(self, tries=4):
        """RViz on Xvfb; it sometimes aborts at start (glibc robust-mutex assertion): retry."""
        for i in range(tries):
            p = self._spawn(['rviz2', '-d', self.rviz, '--ros-args', '-p', 'use_sim_time:=true'],
                            f'rviz{i}.log')
            time.sleep(15)
            if p.poll() is None:
                self.rviz_proc = p
                return
            log(f'rviz exited ({p.returncode}), retrying')
        raise RuntimeError('rviz does not start')

    def _find_view(self):
        """Rectangle of the RViz 3D view: the largest block of the background colour (navy-900)."""
        g = np.asarray(ImageGrab.grab(xdisplay=os.environ['DISPLAY']).convert('RGB')).astype(int)
        bg = (np.abs(g - (11, 18, 32)).sum(axis=2) < 6)
        cols = np.where(bg.mean(axis=0) > 0.25)[0]
        rows = np.where(bg.mean(axis=1) > 0.25)[0]
        if not len(cols) or not len(rows):
            raise RuntimeError('rviz 3D view not found on the virtual display')
        x0, x1, y0, y1 = cols[0], cols[-1] + 1, rows[0], rows[-1] + 1
        log(f'rviz view {x1 - x0}x{y1 - y0} at {x0},{y0}')
        return int(x0), int(y0), int(x1), int(y1)

    def _physics_step(self):
        import glob, xml.etree.ElementTree as ET
        files = sorted(glob.glob(f'/tmp/jo_sim/worlds/{self.world_name}*.sdf'), key=os.path.getmtime)
        try:
            return float(ET.parse(files[-1]).getroot().findtext('world/physics/max_step_size'))
        except (IndexError, TypeError, ValueError):
            return 0.001  # Harmonic's default

    def _find_world(self, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            out = subprocess.run(['gz', 'service', '-l'], capture_output=True, text=True).stdout
            for line in out.splitlines():
                if line.startswith('/world/') and line.endswith('/control'):
                    return line.split('/')[2]
            time.sleep(1)
        raise RuntimeError('no world control service')

    def stop(self):
        try:
            self.records.close()
        except Exception:
            pass
        for p in reversed(self.procs):
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
        for p in self.procs:
            try:
                p.wait(25)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        log(f'stopped after {self.n} frames')

    # ── world ──────────────────────────────────────────────────────────
    def control(self, pause=None, steps=0):
        req = WorldControl()
        # gz-sim applies `pause` on every request: a step must say pause: true or it unpauses
        req.pause = True if steps else bool(pause)
        if steps:
            req.multi_step = steps
        ok, rep = self.gz.request(f'/world/{self.world}/control', req, WorldControl, Boolean, 5000)
        return ok and rep.data

    def sync(self):
        """After stepping or playing outside the rig: re-read the sim time and put the frame
        boundaries back on the 1/FPS grid."""
        self.control(pause=True)
        time.sleep(0.3)
        t = self.sim_time()
        period = 1.0 / FPS
        lead = (math.ceil(t / period - 1e-6) * period - t) % period
        if lead > 1e-6:
            self.control(steps=round(lead / self.step_s))
            time.sleep(0.3)
        self.t = self.sim_time()
        return self.t

    def run(self, *cmd):
        """Runs a command in the container (same ROS domain and Gazebo partition); returns stdout."""
        r = subprocess.run(list(cmd), capture_output=True, text=True, timeout=60)
        log('$', ' '.join(cmd), '->', r.stdout.strip() or r.stderr.strip())
        return r.stdout.strip()

    def sim_time(self):
        out = subprocess.run(['gz', 'topic', '-e', '-n', '1', '-t', f'/world/{self.world}/stats'],
                             capture_output=True, text=True, timeout=10).stdout
        import re
        block = re.search(r'sim_time\s*{([^}]*)}', out)  # protobuf omits zero fields (and a zero block)
        if not block:
            return 0.0
        sec = re.search(r'sec:\s*(\d+)', block.group(1).replace('nsec', 'NSEC'))
        nsec = re.search(r'NSEC:\s*(\d+)', block.group(1).replace('nsec', 'NSEC'))
        return (int(sec.group(1)) if sec else 0) + (int(nsec.group(1)) if nsec else 0) * 1e-9

    def _on_poses(self, msg):
        for p in msg.pose:
            if p.name == 'jo':
                q = p.orientation
                yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
                self.robot = (p.position.x, p.position.y, p.position.z, yaw)

    def camera(self, name, width=1920, height=1080, fov=1.15):
        cam = Camera(self, name, width, height, fov)
        self.cams.append(cam)
        return cam

    # ── ROS ────────────────────────────────────────────────────────────
    def ros_camera(self, name, topic):
        """Saves the latest image of a ROS sensor_msgs/Image topic with every frame (<name>/)."""
        from sensor_msgs.msg import Image as RosImage
        from rclpy.qos import qos_profile_sensor_data
        os.makedirs(os.path.join(self.out, name), exist_ok=True)
        holder = {'msg': None}
        self.ros.create_subscription(RosImage, topic, lambda m: holder.__setitem__('msg', m),
                                     qos_profile_sensor_data)
        self.ros_cams.append((name, holder))

    def _save_ros_cams(self):
        for name, holder in self.ros_cams:
            m = holder['msg']
            if m is None:
                img = PILImage.new('RGB', (640, 360))
            else:
                mode = {'rgb8': 'RGB', 'bgr8': 'RGB', 'rgba8': 'RGBA', 'mono8': 'L'}.get(m.encoding, 'RGB')
                img = PILImage.frombytes(mode, (m.width, m.height), bytes(m.data))
                if m.encoding == 'bgr8':
                    img = PILImage.merge('RGB', img.split()[::-1])
            img.convert('RGB').save(os.path.join(self.out, name, f'{self.n:05d}.png'), compress_level=1)

    def cmd_vel(self, vx, wz):
        m = self._Twist()
        m.linear.x, m.angular.z = float(vx), float(wz)
        self.cmd_pub.publish(m)

    def goal(self, x, y, yaw, frame='map'):
        m = self._PoseStamped()
        m.header.frame_id = frame
        m.pose.position.x, m.pose.position.y = float(x), float(y)
        w, _, _, z = quat_rpy(0, 0, yaw)
        m.pose.orientation.w, m.pose.orientation.z = w, z
        self.goal_pub.publish(m)

    def gps_waypoints(self, points, datum):
        """Sends FollowGPSWaypoints (Nav2's GPS waypoint follower, as send_gps_waypoints.py does).
        points: world (x, y) [m] (Gazebo is east-north-up); datum: (lat, lon) of the world origin."""
        from rclpy.action import ActionClient
        from geographic_msgs.msg import GeoPose
        from nav2_msgs.action import FollowGPSWaypoints
        if not hasattr(self, '_gps_client'):
            self._gps_client = ActionClient(self.ros, FollowGPSWaypoints, 'follow_gps_waypoints')
        end = time.time() + 30
        while not self._gps_client.server_is_ready() and time.time() < end:
            self.spin(0.2)
        lat0, lon0 = datum
        R = 6378137.0
        goal = FollowGPSWaypoints.Goal()
        for x, y in points:
            gp = GeoPose()
            gp.position.latitude = lat0 + math.degrees(y / R)
            gp.position.longitude = lon0 + math.degrees(x / (R * math.cos(math.radians(lat0))))
            gp.orientation.w = 1.0
            goal.gps_poses.append(gp)
        self._gps_future = self._gps_client.send_goal_async(goal)
        log(f'GPS waypoints sent: {len(points)}')
        return goal

    def spin(self, seconds=0.0):
        import rclpy
        end = time.time() + seconds
        while True:
            rclpy.spin_once(self.ros, timeout_sec=0.0)
            if time.time() >= end:
                break
            time.sleep(0.01)

    # ── frames ─────────────────────────────────────────────────────────
    def ros_value(self, key, topic, msg_type, fn, qos=10):
        """Logs fn(latest message) of a ROS topic in every frame record, under `key`."""
        holder = {}
        self.ros.create_subscription(msg_type, topic, lambda m: holder.__setitem__('m', m), qos)
        self.ros_values.append((key, holder, fn))

    def frame(self, record=True, xvfb_wait=0.15, stride=1, **values):
        """Advance `stride` frame periods and save every camera (and the Xvfb display): stride 2
        records every other frame (a 2x time-lapse at half the rendering cost)."""
        steps = round(stride / FPS / self.step_s)
        self.spin()
        self.control(steps=steps)
        self.t += steps * self.step_s
        imgs = [(c, c.wait(self.t)) for c in self.cams]
        self.spin(xvfb_wait if self.rviz or self.xvfb_crop else (0.05 if self.ros_cams else 0.0))
        if not record:
            return
        for c, img in imgs:
            img.save(os.path.join(c.dir, f'{self.n:05d}.png'), compress_level=1)
        self._save_ros_cams()
        if self.rviz or self.xvfb_crop:
            os.makedirs(os.path.join(self.out, 'xvfb'), exist_ok=True)
            g = ImageGrab.grab(xdisplay=os.environ['DISPLAY'])
            if self.xvfb_crop:
                g = g.crop(self.xvfb_crop)
            g.save(os.path.join(self.out, 'xvfb', f'{self.n:05d}.png'), compress_level=1)
        for key, holder, fn in self.ros_values:
            if 'm' in holder:
                values[key] = fn(holder['m'])
        self.records.write(json.dumps({'n': self.n, 't': round(self.t, 4), 'robot': self.robot,
                                       **self.extra, **values}) + '\n')
        self.n += 1
        if self.n % 30 == 0:
            log(f'frame {self.n} t={self.t:.2f}')

    def snap(self, wait=1.0, **values):
        """Records the cameras' latest images without stepping (after a step done elsewhere)."""
        time.sleep(wait)
        for c in self.cams:
            with c.lock:
                c.latest[1].save(os.path.join(c.dir, f'{self.n:05d}.png'), compress_level=1)
        self.records.write(json.dumps({'n': self.n, 't': round(self.cams[0].latest[0], 4), **self.extra,
                                       **values}) + '\n')
        self.n += 1

    def live_begin(self):
        """Start keeping every camera image (for a stretch where the world runs by itself)."""
        for c in self.cams:
            with c.lock:
                c.buffer = []

    def live_end(self, **values):
        """Writes the images kept since live_begin as frames, in sim-time order (the world should be
        paused again). Only the main camera's stamps drive the frame records."""
        bufs = []
        for c in self.cams:
            with c.lock:
                bufs.append(c.buffer or [])
                c.buffer = None
        if not bufs or not bufs[0]:
            return 0
        for k, (t, img) in enumerate(bufs[0]):
            img.save(os.path.join(self.cams[0].dir, f'{self.n:05d}.png'), compress_level=1)
            for c, b in zip(self.cams[1:], bufs[1:]):
                if b:
                    b[min(k, len(b) - 1)][1].save(os.path.join(c.dir, f'{self.n:05d}.png'), compress_level=1)
            self.records.write(json.dumps({'n': self.n, 't': round(t, 4), 'live': True, **values}) + '\n')
            self.n += 1
        log(f'live: {len(bufs[0])} frames, t {bufs[0][0][0]:.2f} to {bufs[0][-1][0]:.2f}')
        return len(bufs[0])

    def run_for(self, seconds, record=False, **kw):
        """Advance without recording (or recording) for `seconds` of sim time."""
        for _ in range(round(seconds * FPS)):
            self.frame(record=record, **kw)


def main(shot_fn):
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(1))
    signal.signal(signal.SIGHUP, lambda *a: sys.exit(1))
    shot_fn()
