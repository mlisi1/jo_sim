"""Runs INSIDE the jo_sim container (fed on stdin by docs/gen/measure_performance.py).

For each configuration: launch sim_bringup headless, let it settle, then over a wall-clock window
measure the real-time factor (sim time advanced / wall time), the CPU cores used by the launch's
process group, and the GPU utilization and memory (nvidia-smi). Prints one JSON line per
configuration on stdout. ROS_DOMAIN_ID and GZ_PARTITION come from the caller.
"""
import json, os, re, signal, subprocess, sys, time

SETTLE_S = float(os.environ.get('PERF_SETTLE', '45'))
WINDOW_S = float(os.environ.get('PERF_WINDOW', '30'))
WORLD = os.environ.get('PERF_WORLD', 'office_cpr')
NO_SENSORS = ['lidar:=false', 'imu:=false', 'gnss:=false', 'front_cam:=false', 'back_cam:=false']
CONFIGS = [
    ('Gazebo and the robot, no sensors', NO_SENSORS),
    ('+ lidar only', ['lidar:=true'] + NO_SENSORS[1:]),
    ('+ IMU and GNSS only', ['lidar:=false', 'imu:=true', 'gnss:=true', 'front_cam:=false', 'back_cam:=false']),
    ('+ one RealSense only', ['lidar:=false', 'imu:=false', 'gnss:=false', 'front_cam:=true', 'back_cam:=false']),
    ('All sensors (`--nav none`)', ['gnss:=true', 'front_cam:=true', 'back_cam:=true']),
    ('All sensors, no cameras', ['gnss:=true', 'front_cam:=false', 'back_cam:=false']),
    ('All sensors + GLIM, EKF, Nav2 (`--nav local`)',
     ['front_cam:=true', 'back_cam:=true', 'localization:=true', 'navigation:=true', 'rviz:=false']),
    ('All sensors + GPS stack (`--nav gps`)',
     ['gnss:=true', 'front_cam:=true', 'back_cam:=true', 'localization_gps:=true', 'navigation_gps:=true',
      'rviz:=false']),
]


def sim_time():
    out = subprocess.run(['gz', 'topic', '-e', '-n', '1', '-t', '/stats'], capture_output=True,
                         text=True, timeout=10).stdout
    m = re.search(r'sim_time\s*{\s*sec:\s*(\d+)(?:\s*nsec:\s*(\d+))?', out)
    return int(m.group(1)) + int(m.group(2) or 0) * 1e-9 if m else None


def cpu_seconds(pgid):
    tick = os.sysconf('SC_CLK_TCK')
    total = 0
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            fields = open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid:  # field 5 (pgrp), after state and ppid
                total += int(fields[11]) + int(fields[12])  # utime + stime
        except (OSError, IndexError, ValueError):
            pass
    return total / tick


def gpu_sample():
    out = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used',
                          '--format=csv,noheader,nounits'], capture_output=True, text=True).stdout
    u, m = out.strip().split(',')
    return float(u), float(m)


def run(name, args):
    cmd = ['ros2', 'launch', 'jo_sim', 'sim_bringup.launch.py', f'world:={WORLD}', 'gui:=false',
           'paused:=false', 'gz_verbosity:=1'] + args
    log = open(f"/tmp/jo_sim/perf_{len(name)}.log", 'w')
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        time.sleep(SETTLE_S)
        if proc.poll() is not None:
            return {'name': name, 'args': args, 'error': 'launch died'}
        s0, c0, t0 = sim_time(), cpu_seconds(proc.pid), time.time()
        gpu = []
        while time.time() - t0 < WINDOW_S:
            gpu.append(gpu_sample())
            time.sleep(2.0)
        s1, c1, t1 = sim_time(), cpu_seconds(proc.pid), time.time()
        wall = t1 - t0
        return {'name': name, 'args': args,
                'rtf': round((s1 - s0) / wall, 2) if s0 is not None and s1 is not None else None,
                'cpu_cores': round((c1 - c0) / wall, 1),
                'gpu_util': round(sum(g[0] for g in gpu) / len(gpu)),
                'gpu_mem_mib': round(max(g[1] for g in gpu))}
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
        time.sleep(5)


def main():
    os.makedirs('/tmp/jo_sim', exist_ok=True)
    only = sys.argv[1:]  # optional config indices

    def bail(*_):
        sys.exit(1)  # the finally in run() stops the launch
    signal.signal(signal.SIGTERM, bail)
    signal.signal(signal.SIGHUP, bail)
    idle = gpu_sample()
    print(json.dumps({'idle_gpu_util': idle[0], 'idle_gpu_mem_mib': idle[1], 'world': WORLD,
                      'settle_s': SETTLE_S, 'window_s': WINDOW_S}), flush=True)
    for i, (name, args) in enumerate(CONFIGS):
        if only and str(i) not in only:
            continue
        print(f'[{i}] {name}', file=sys.stderr, flush=True)
        print(json.dumps(run(name, args)), flush=True)


if __name__ == '__main__':
    main()
