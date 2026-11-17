"""office_cpr, Jo driving forward on /cmd_vel the whole time; the real sim_control commands and
their real output: status, pause (Jo freezes mid-motion), step 500 twice (half a second each, at
the 1 ms physics step), play (Jo drives on), pause.
While the world runs, every camera image is kept (live segments, in sim-time order); while it is
paused, one image after each command (snaps).
Records main (a fixed wide camera beside Jo's path) and, in frames.jsonl:
- snaps: 'term': [command, output];
- live frames: 'live': segment number; at the end of each segment, 'events': [[command, output,
  sim time the command printed], ...].
Used by: sim-control page."""
import re
import threading

VX = 0.2


def shot():
    rig = Rig('sim_control', world='office_cpr', launch=['yaw:=1.5708'])
    stop = threading.Event()
    try:
        rig.start(settle=20)
        cam = rig.camera('main', 1152, 1080, fov=1.05)
        x, y, z, _ = rig.robot
        cam.look((x + 4.4, y + 0.8, z + 1.6), (x, y + 1.3, z - 0.1))
        ctl = lambda *a: rig.run('ros2', 'run', 'jo_sim', 'sim_control', *a)

        def drive():                       # like a teleop node: /cmd_vel at 10 Hz
            while not stop.is_set():
                rig.cmd_vel(VX, 0.0)
                time.sleep(0.1)
        threading.Thread(target=drive, daemon=True).start()
        rig.frame(record=False)

        def sim_t(out):
            m = re.search(r'sim time ([0-9.]+)', out)
            return float(m.group(1)) if m else None

        # segment 0: running (the play itself is not shown: the video opens with Jo driving)
        ctl('play')
        time.sleep(1.0)
        rig.live_begin()
        time.sleep(1.6)
        st = ctl('status')
        time.sleep(1.0)
        pa = ctl('pause')
        rig.live_end(live=0, events=[['./jo ctl status', st, sim_t(st)], ['./jo ctl pause', pa, sim_t(pa)]])
        for _ in range(2):
            out = ctl('step', '500')
            rig.snap(term=['./jo ctl step 500', out])
        # segment 1: running again
        rig.live_begin()
        pl = ctl('play')
        time.sleep(2.2)
        pa = ctl('pause')
        rig.live_end(live=1, events=[['./jo ctl play', pl, sim_t(pl)], ['./jo ctl pause', pa, sim_t(pa)]])
        log(f'Jo at {rig.robot[:2]}')
    finally:
        stop.set()
        rig.stop()


main(shot)
