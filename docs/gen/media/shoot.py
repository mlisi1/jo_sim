#!/usr/bin/env python3
"""Shoots one docs video shot with the frame-locked rig (docs/gen/media/rig.py).

    python3 docs/gen/media/shoot.py SHOT          e.g. orbit_office  (docs/gen/media/shots/SHOT.py)

Starts the virtual display (Xvfb :99) if needed, writes the docs RViz configs (navy background,
window filling the virtual screen) into the container, runs rig.py + the shot script in the container (ROS domain 79,
Gazebo partition jo_sim_docs, the GUIs on :99 with software GL, Gazebo headless on the GPU), and
copies the frames to ~/.cache/jo_sim_media/rig/SHOT/. Then docs/gen/media/compose.py makes the video.
Nothing is shown on the real screens.
"""
import os, pathlib, shutil, subprocess, sys, time

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
CONTAINER = 'jo_sim-jo-sim-1'
DISPLAY, SCREEN = ':99', '3200x1800x24'
CACHE = pathlib.Path.home() / '.cache' / 'jo_sim_media' / 'rig'
RVIZ_SOURCES = {'sim': 'jo_sim/rviz/sim.rviz', 'nav': 'jo_navigation/rviz/navigation.rviz'}
RVIZ_W, RVIZ_H = 3200, 1800  # the whole Xvfb screen; shots crop the 3D view


def ensure_xvfb():
    if pathlib.Path(f'/tmp/.X11-unix/X{DISPLAY[1:]}').exists():
        size = subprocess.run(['xdpyinfo', '-display', DISPLAY], capture_output=True, text=True).stdout
        if SCREEN.rsplit('x', 1)[0] in size:
            return
        for pid in subprocess.run(['pgrep', '-f', f'^Xvfb {DISPLAY} '], capture_output=True,
                                  text=True).stdout.split():
            os.kill(int(pid), 15)  # wrong size: restart it
        time.sleep(1)
    subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', SCREEN, '-nolisten', 'tcp'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        if pathlib.Path(f'/tmp/.X11-unix/X{DISPLAY[1:]}').exists():
            return
        time.sleep(0.1)
    sys.exit('Xvfb did not start')


def docs_rviz(name):
    """A copy of an RViz config for the docs: navy background, window at (0, 0) filling Xvfb.

    The layout (docks, panels) stays as in the source: RViz refuses configs without panels or with
    the image displays disabled. The rig crops the 3D view out of the screen grab instead."""
    cfg = yaml.safe_load((ROOT / RVIZ_SOURCES[name]).read_text())
    cfg['Visualization Manager']['Global Options']['Background Color'] = '11; 18; 32'  # navy-900
    cfg.setdefault('Window Geometry', {}).update({'X': 0, 'Y': 0, 'Width': RVIZ_W, 'Height': RVIZ_H})
    return cfg


def write_rviz(name, cfg):
    subprocess.run(['docker', 'exec', '-i', CONTAINER, 'bash', '-c', f'cat > /tmp/jo_sim/rviz_docs/{name}.rviz'],
                   input=yaml.safe_dump(cfg, sort_keys=False), text=True, check=True)


def main():
    shot = sys.argv[1]
    script = (HERE / 'shots' / f'{shot}.py').read_text()
    ensure_xvfb()
    # RViz configs the shots can use: /tmp/jo_sim/rviz_docs/{sim,nav}.rviz
    subprocess.run(['docker', 'exec', CONTAINER, 'mkdir', '-p', '/tmp/jo_sim/rviz_docs'], check=True)
    for name in RVIZ_SOURCES:
        write_rviz(name, docs_rviz(name))
    code = (HERE / 'rig.py').read_text() + '\n\n# ── shot ──\n' + script
    env = ['-e', 'ROS_DOMAIN_ID=79', '-e', 'GZ_PARTITION=jo_sim_docs', '-e', f'DISPLAY={DISPLAY}',
           '-e', '__NV_PRIME_RENDER_OFFLOAD=0', '-e', '__GLX_VENDOR_LIBRARY_NAME=mesa',
           '-e', 'QT_QPA_PLATFORM=xcb']
    cmd = ('source /opt/ros/jazzy/setup.bash; source /home/ros/install/setup.bash; python3 -; rc=$?; '
           'ros2 daemon stop >/dev/null 2>&1; exit $rc')
    t0 = time.time()
    r = subprocess.run(['docker', 'exec', '-i', *env, CONTAINER, 'bash', '-c', cmd], input=code, text=True)
    dst = CACHE / shot
    shutil.rmtree(dst, ignore_errors=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['docker', 'cp', f'{CONTAINER}:/tmp/jo_sim/rig/{shot}', str(dst)], check=False)
    subprocess.run(['docker', 'exec', CONTAINER, 'rm', '-rf', f'/tmp/jo_sim/rig/{shot}'])
    left = subprocess.run(['docker', 'exec', CONTAINER, 'bash', '-c',
                           'ps -eo pid,cmd | grep -E "gz sim|ros2 launch|rviz2|glim" | grep -v grep'],
                          capture_output=True, text=True).stdout
    print(f'{shot}: exit {r.returncode}, {time.time() - t0:.0f} s, frames in {dst}'
          + (f'\nWARNING still running in the container:\n{left}' if left.strip() else ''))
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
