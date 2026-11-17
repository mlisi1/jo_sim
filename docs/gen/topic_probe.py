"""Runs INSIDE the jo_sim container (fed on stdin by docs/gen/gen_topics.py).

Starts launch_sim headless, waits for it to settle, then for every topic records its type, the
publishing and subscribing nodes, the publishers' QoS, the header frame_id and the rate (in sim
time), plus the TF edges and every node's parameters. Prints one JSON document on stdout; the
launch log goes to /tmp/jo_sim/gen_topics.log. ROS_DOMAIN_ID and GZ_PARTITION come from the caller.
"""
import json, os, signal, struct, subprocess, sys, time

SETTLE_S = float(os.environ.get('PROBE_SETTLE', '30'))
WINDOW_S = float(os.environ.get('PROBE_WINDOW', '10'))
LAUNCH = ['ros2', 'launch', 'jo_sim', 'launch_sim.launch.py', 'gui:=false', 'follow:=false',
          'gz_verbosity:=2'] + sys.argv[1:]
# Topics of the probe itself and of the ROS infrastructure
IGNORE = {'/rosout', '/parameter_events'}
# image_transport plugin topics: subscribing makes the publisher encode, so only list them
TRANSPORTS = ('/compressed', '/compressedDepth', '/theora', '/zstd', '/ffmpeg')


def log(*a):
    print(*a, file=sys.stderr, flush=True)


BIG = ('sensor_msgs/msg/PointCloud2', 'sensor_msgs/msg/Image')


def group_of(name, mtype):
    """Topics are measured in passes: six 30 Hz clouds and images in one process starved the small
    fast topics (the IMU read 27 Hz instead of 200)."""
    if mtype not in BIG:
        return 'small'
    return 'sim' if name.startswith('/sim/') else 'interface'


def probe(domain, group):
    import rclpy
    from rclpy.qos import (QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy)
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    ctx = rclpy.Context()
    rclpy.init(context=ctx, domain_id=domain)
    node = rclpy.create_node('gen_topics_probe', context=ctx)
    time.sleep(3.0)  # discovery
    me = node.get_fully_qualified_name()

    def names(infos):
        return sorted({(i.node_namespace.rstrip('/') + '/' + i.node_name) for i in infos} - {me})

    def enum(v):
        return v.name.lower() if hasattr(v, 'name') else str(v)

    topics, stats, clock = {}, {}, []
    tf_edges = {}
    for name, types in node.get_topic_names_and_types():
        if name in IGNORE or name.startswith('/testudo'):
            continue
        pubs = node.get_publishers_info_by_topic(name)
        subs = node.get_subscriptions_info_by_topic(name)
        qos = sorted({(enum(p.qos_profile.reliability), enum(p.qos_profile.durability),
                       p.qos_profile.depth) for p in pubs})
        topics[name] = {'type': types[0], 'publishers': names(pubs), 'subscribers': names(subs),
                        'qos': [list(q) for q in qos]}
        if not pubs or name.endswith(TRANSPORTS):
            continue
        if group_of(name, types[0]) != group and name != '/clock':
            continue
        mclass = get_message(types[0])
        has_header = 'header' in mclass.get_fields_and_field_types()
        st = stats[name] = {'n': 0, 'frame': None}

        def cb(data, name=name, st=st, has_header=has_header, mclass=mclass):
            st['n'] += 1
            if has_header and st['frame'] is None:
                # CDR: 4-byte encapsulation, stamp (8 bytes), then frame_id: uint32 length + chars
                le = data[1] == 1
                (n,) = struct.unpack_from('<I' if le else '>I', data, 12)
                st['frame'] = bytes(data[16:16 + n - 1]).decode(errors='replace')
            if name == '/clock':
                m = deserialize_message(data, mclass)
                clock.append(m.clock.sec + m.clock.nanosec * 1e-9)
            elif name in ('/tf', '/tf_static'):
                m = deserialize_message(data, mclass)
                for t in m.transforms:
                    tf_edges[t.child_frame_id] = (t.header.frame_id, name == '/tf_static')

        best_effort = any(p.qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT for p in pubs)
        latched = all(p.qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL for p in pubs)
        # Deep queues for the small fast topics (IMU 200 Hz, ground truth 100 Hz): with depth 10
        # they were undercounted 4x while the probe was busy with the 30 Hz clouds
        big = types[0] in BIG
        q = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=100 if latched else (10 if big else 1000),
                       reliability=ReliabilityPolicy.BEST_EFFORT if best_effort else ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL if latched else DurabilityPolicy.VOLATILE)
        node.create_subscription(mclass, name, cb, q, raw=True)
        st['latched'] = latched

    log(f'probing {len(stats)} topics ({group}) for {WINDOW_S} s')
    ex = rclpy.executors.SingleThreadedExecutor(context=ctx)
    ex.add_node(node)
    t0 = time.time()
    counts0 = None
    while time.time() - t0 < WINDOW_S:
        ex.spin_once(timeout_sec=0.02)
        if counts0 is None and time.time() - t0 > 1.0 and clock:
            # rates are counted from here, after the subscriptions have matched
            counts0 = ({k: v['n'] for k, v in stats.items()}, clock[-1])
    span = (clock[-1] - counts0[1]) if counts0 and clock else None
    for k, st in stats.items():
        if st.pop('latched') or not span:
            st['hz'] = None
        else:
            st['hz'] = round((st['n'] - counts0[0][k]) / span, 1)
        topics[k].update(st)
    ex.shutdown()
    node.destroy_node()
    rclpy.shutdown(context=ctx)
    return topics, tf_edges, span


def params(nodes):
    import yaml
    out = {}
    for n in nodes:
        r = subprocess.run(['ros2', 'param', 'dump', n], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            try:
                out[n] = list(yaml.safe_load(r.stdout).values())[0]['ros__parameters']
            except Exception:
                pass
    return out


def main():
    os.makedirs('/tmp/jo_sim', exist_ok=True)
    domain = int(os.environ['ROS_DOMAIN_ID'])
    with open('/tmp/jo_sim/gen_topics.log', 'w') as lf:
        proc = subprocess.Popen(LAUNCH, stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)

    def stop(*_):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)

    signal.signal(signal.SIGTERM, lambda *a: (stop(), sys.exit(1)))
    signal.signal(signal.SIGHUP, lambda *a: (stop(), sys.exit(1)))
    try:
        log(f'launched (pgid {proc.pid}), settling {SETTLE_S} s')
        time.sleep(SETTLE_S)
        if proc.poll() is not None:
            raise SystemExit('launch died, see /tmp/jo_sim/gen_topics.log')
        topics, tf_edges, span = probe(domain, 'small')
        for group in ('interface', 'sim'):
            t2, _, _ = probe(domain, group)
            for k, v in t2.items():
                if group_of(k, v['type']) == group and 'hz' in v:
                    topics[k].update({f: v[f] for f in ('n', 'frame', 'hz')})
        nodes = sorted({n for t in topics.values() for n in t['publishers'] + t['subscribers']})
        log(f'dumping parameters of {len(nodes)} nodes')
        json.dump({'launch': LAUNCH, 'sim_span_s': span, 'topics': topics,
                   'tf': {c: list(p) for c, p in tf_edges.items()}, 'params': params(nodes)},
                  sys.stdout, indent=1, default=str)
    finally:
        stop()


if __name__ == '__main__':
    main()
