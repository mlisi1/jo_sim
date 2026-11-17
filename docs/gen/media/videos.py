#!/usr/bin/env python3
"""Composes the docs videos from the rig shots (docs/gen/media/shots/, shot with shoot.py).

    python3 docs/gen/media/videos.py first_run [...]     # or: all
    python3 docs/gen/media/videos.py first_run --preview # a contact sheet only, in /tmp

Each video is a function below; the shots it needs are listed in its docstring.
"""
import os, sys

from compose import *  # noqa: F403


def first_run():
    """Shots: office_drive."""
    rec = records('office_drive')
    drive0 = next(r['n'] for r in rec if r.get('part') == 'drive')
    g = frames('office_drive').cut(drive0)
    rv = frames('office_drive', 'xvfb').cut(drive0)
    front = frames('office_drive', 'front', size=(640, 360)).cut(drive0)
    body = split(g, rv, ax_b=0.2)
    body = overlay(body, lambda d, i: (chip(d, 'Gazebo', 28, 28, dot=CYAN), chip(d, 'RViz', W // 2 + 28, 28, dot=AMBER)))
    body = pip(body, front, corner='tr', width=440, label='front camera')
    body = caption(body, './jo sim', 'Teleop on /cmd_vel; lidar and camera clouds in RViz', n_in=15)
    return body.fade(10, 10)


def nav_local():
    """Shots: nav_local."""
    rec = [r for r in records('nav_local') if 'n' in r]
    rv = frames('nav_local', 'xvfb')
    g = frames('nav_local', size=(960, 540))
    body = pip(rv, g, corner='tr', width=620, label='Gazebo')
    goal_of = [r.get('goal', 0) for r in rec]
    labels = ['Goal 1: 4.5 m ahead', 'Goal 2: back, facing the start']

    def marks(d, i):
        chip(d, labels[goal_of[min(i, len(goal_of) - 1)]], 36, 36, size=30, dot=AMBER)
    body = overlay(body, marks)
    body = caption(body, './jo sim -n local', 'GLIM + EKF localization, Nav2 (mapless); goals on /goal_pose')
    return body.speed(1.6).fade(10, 12)


def sim_control():
    """Shots: sim_control. Left: Gazebo (live segments 1:1, a held frame while a command is typed
    in a paused stretch); right: the terminal with the real commands and outputs, each output
    shown at the frame whose sim time it printed."""
    rec = [r for r in records('sim_control') if 'n' in r]
    g = frames('sim_control', size=(1152, 1080), crop=(0, 0, 1100, 1031))
    cps, lead, hold = 28, 14, 40                           # typing speed, pause before output, hold

    def typed(cmd):
        return round(len(cmd) / cps * FPS) + lead
    # the source sequence, as segments in order: ('live', [records]) or ('snap', record)
    segs = []
    for r in rec:
        if 'live' in r:
            if segs and segs[-1][0] == 'live' and segs[-1][1][0]['live'] == r['live']:
                segs[-1][1].append(r)
            else:
                segs.append(('live', [r]))
        else:
            segs.append(('snap', r))
    src, lines = [], []                                    # src: output frame -> source frame n
    for kind, x in segs:
        if kind == 'snap':                                 # paused: type, then the new frame
            cmd, out = x['term']
            lines.append((len(src), 'cmd', cmd))
            src += [src[-1]] * typed(cmd)
            lines.append((len(src), 'out', out_spans(out)))
            src += [x['n']] * hold
            continue
        live, events = x, x[-1].get('events', [])
        start = len(src)
        for cmd, out, t in events:                         # outputs at their sim time
            k = 0 if t is None else min(range(len(live)), key=lambda q: abs(live[q]['t'] - t))
            if cmd.endswith('play'):
                k = 0                                      # play prints as the world starts
            lines.append((start + k - typed(cmd), 'cmd', cmd))
            lines.append((start + k, 'out', out_spans(out)))
        src += [r['n'] for r in live]
        if events and events[-1][0].endswith('pause'):
            src += [src[-1]] * hold
    lines.sort(key=lambda l: l[0])
    shift = max(0, -lines[0][0]) if lines else 0           # a command typed before the first frame
    src = [src[0]] * shift + src
    lines = [(t + shift, k, v) for t, k, v in lines]
    n = len(src) + 20
    left = Clip(n, lambda i: g(src[min(i, len(src) - 1)]))
    term = terminal(n, lines, size=(W - 1152, H), title='~/jo_sim', font_size=25)
    body = split(left, term, ratio=0.6, gap=0)
    body = overlay(body, lambda d, i: chip(d, 'Gazebo, Jo driving on /cmd_vel', 28, 28, dot=CYAN))
    return caption(body, 'Pause, step, play', 'Paused, Jo freezes mid-motion; step 500 = 0.5 s of sim time').fade(8, 12)


def out_spans(out):
    """Colours a sim_control status line: world, state, the rest."""
    if not out:
        return [('', MUTED)]
    world, _, rest = out.partition(': ')
    state, _, tail = rest.partition(', ')
    return [(world + ': ', MUTED), (state, AMBER if state == 'paused' else GREEN), (', ' + tail, MUTED)]


def scenario():
    """Shots: scenario (the real runner's output, with the frame where each line appeared)."""
    import json
    rec = [r for r in records('scenario') if 'n' in r]
    lines_raw = json.load(open(RIG / 'scenario' / 'cmd_lines.json'))
    g = frames('scenario', size=(1152, 1080))
    k = 3                                                   # speed-up of the run
    run = g.speed(k)
    head = 20                                               # frames before the run (the command typed)
    tail = 4 * FPS                                          # hold at the end, with the verdict
    n = head + len(run) + tail

    def colour(line):
        body = line.replace('[scenario] ', '')
        c = MUTED
        if 'PASS' in body or ' ok ' in f' {body} ' or 'succeeded' in body:
            c = GREEN
        if 'FAIL' in body or 'ERROR' in body or 'timeout' in body:
            c = RED
        return [('[scenario] ', (100, 116, 139)), (body, c)] if line.startswith('[scenario]') else [(line, MUTED)]
    shown = [(n_, l) for n_, l in lines_raw if l.startswith('[scenario]') and 'output:' not in l]
    lines = [(0, 'cmd', './jo scenario office_crossing')]
    for n_, l in shown:
        at = head + (min(n_, len(rec)) // k if n_ < len(rec) else len(run) + 10)
        lines.append((max(at, 18), 'out', colour(l)))
    left = Clip(n, lambda i: run(i - head))
    term = terminal(n, lines, size=(W - 1152, H), title='~/jo_sim', font_size=22)
    body = split(left, term, ratio=0.6, gap=0)
    body = overlay(body, lambda d, i: (chip(d, 'office_crossing', 28, 28, dot=CYAN),
                                       chip(d, f'{k}×', 330, 28, dot=None) if head <= i < head + len(run) else None))
    body = caption(body, 'Scenarios', "A walker crosses Jo's path and yields; verdict from the ground truth")
    return body.fade(8, 12)


def tag(clip, text, sub=None):
    """The reel's small lower-left label (shorter than caption())."""
    return caption(clip, text, sub, n_in=10)


def hero():
    """Shots: office_drive, nav_local, nav_gps, scenario, glim_city. ~25 s, loops."""
    rec = records('office_drive')
    drive0 = next(r['n'] for r in rec if r.get('part') == 'drive')
    orbit = frames('office_drive').cut(10, drive0)
    drive = split(frames('office_drive').cut(drive0 + 40), frames('office_drive', 'xvfb').cut(drive0 + 40), ax_b=0.2)
    nav = pip(frames('nav_local', 'xvfb'), frames('nav_local', size=(960, 540)), corner='tr', width=560)
    gps = frames('nav_gps', crop=GPS_CROP)
    scen = frames('scenario').speed(3)
    glim = frames('glim_city', 'xvfb')
    s = FPS
    clips = [
        card(int(2.6 * s), 'Jo, simulated', 'The jo-zotac robot in Gazebo Harmonic, with the real ROS interface'),
        tag(orbit.speed(1.2).cut(0, int(3.2 * s)), 'Gazebo Harmonic', 'The real robot\'s URDF and TFs'),
        tag(drive.cut(0, int(3.6 * s)), 'The real sensors', 'VLP-16 lidar, two RealSense D456, Xsens IMU and GNSS'),
        tag(nav.speed(2.5).cut(0, int(3.6 * s)), 'The robot\'s navigation stack', 'GLIM + EKF localization, Nav2'),
        tag(gps.speed(2).cut(0, int(3.4 * s)), 'GPS waypoints', 'In georeferenced worlds'),
        tag(glim.cut(len(glim) * 2 // 3, len(glim) * 2 // 3 + int(3.0 * s)), 'GLIM maps', 'Built live, saved with save_map'),
        tag(scen.cut(len(scen) // 3, len(scen) // 3 + int(3.0 * s)), 'Scenarios', 'Missions with pass/fail criteria'),
        card(int(3.0 * s), 'Jo, simulated', 'One container, one command', code='./jo sim'),
    ]
    return concat(*clips, xfade=10)


GPS_CROP = (360, 202, 1560, 877)   # the centre of the aerial frames (the camera targets Jo): 1.6x


def nav_gps():
    """Shots: nav_gps (2x time-lapse: every other frame)."""
    import math
    rec = [r for r in records('nav_gps') if 'n' in r]
    g = frames('nav_gps', crop=GPS_CROP)
    wps = rec[0]['waypoints']
    reached, k = [], 0
    for r in rec:                                   # the waypoint Jo is heading to, per frame
        x, y = r['robot'][:2]
        if k < len(wps) - 1 and math.hypot(x - wps[k][0], y - wps[k][1]) < 1.5:
            k += 1
        reached.append(k)

    def hud(d, i):
        r = rec[min(i, len(rec) - 1)]
        chip(d, f'Waypoint {reached[min(i, len(rec) - 1)] + 1} of {len(wps)}', 36, 36, size=30, dot=AMBER)
        if r.get('gnss'):
            lat, lon = r['gnss']
            f = font(30, mono=True)
            text = f'/gnss  {lat:.6f}  {lon:.6f}'
            tw = d.textlength(text, font=f)
            d.rounded_rectangle((W - tw - 96, 36, W - 36, 96), 14, fill=NAVY_900)
            d.text((W - tw - 66, 48), text, font=f, fill=CYAN_300)
    body = overlay(g, hud)
    body = caption(body, './jo sim -w small_city -n gps', 'Two GPS waypoints to follow_gps_waypoints (2× speed)')
    return body.fade(10, 12)


def glim_map():
    """Shots: glim_city (3x time-lapse, played at 4.5x). RViz main (GLIM's map by height, the current scan in cyan,
    Nav2's path in amber), Gazebo top right."""
    start = 165        # GLIM publishes its first map at frame ~192 (its first submap): skip most of the wait
    body = pip(frames('glim_city', 'xvfb').cut(start), frames('glim_city', size=(960, 540)).cut(start),
               corner='tr', width=480).speed(1.5)
    body = caption(body, './jo sim -w small_city -n local', "GLIM's map growing as Nav2 drives Jo through the city (4.5× speed)")
    return body.fade(10, 12)


# per-video encoder settings: dense point clouds compress badly at the default CRF 28
ENCODE = {'glim_map': {'crf': 34, 'size': (1280, 720)}, 'hero': {'crf': 31}}


VIDEOS_ = {'glim_map': glim_map, 'nav_gps': nav_gps, 'hero': hero, 'scenario': scenario, 'first_run': first_run, 'nav_local': nav_local, 'sim_control': sim_control}


if __name__ == '__main__':
    names = sys.argv[1:]
    prev = '--preview' in names
    names = [n for n in names if not n.startswith('--')]
    if names == ['all']:
        names = list(VIDEOS_)
    for n in names:
        clip = VIDEOS_[n]()
        if prev:
            print(preview(clip, os.path.join(os.environ.get('PREVIEW_DIR', '/tmp'), f'{n}_preview.jpg')))
        else:
            render(clip, n, **ENCODE.get(n, {}))
