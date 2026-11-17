"""The real scenario runner on office_crossing (local navigation, a person walking across Jo's path).
The runner launches the sim and drives the mission; the rig attaches once it is ready, steps the
world frame by frame, and keeps every line the runner prints (cmd_lines.json) with its frame number.
Records main (a high camera over the crossing). Used by: scenarios page, hero reel."""

import re

N_GOALS = 2


def shot():
    rig = Rig('scenario', world='office_cpr')
    try:
        rig.attach(['ros2', 'run', 'jo_sim', 'scenario', 'office_crossing'], ready='ready at sim time')
        cam = rig.camera('main', 1920, 1080)
        for i in range(150 * FPS):
            u = min(1.0, i / (40 * FPS))
            eye = (4.6 - 1.2 * smooth(u), -1.6 + 0.6 * smooth(u), 4.4)
            cam.look(eye, (-0.2, 2.6, 0.2))
            rig.frame()
            done = sum(1 for _, l in rig.cmd_lines if re.match(r'\[scenario\] goal \d+: \w+ in ', l))
            if done >= N_GOALS:            # the runner stops the sim right after the last goal
                break
            if rig.cmd_proc.poll() is not None:
                log('the runner exited early')
                break
        rig.control(pause=False)            # let the runner finish (it stops the sim itself)
        rig.cmd_proc.wait(120)
        time.sleep(1)
    finally:
        if hasattr(rig, 'cmd_lines'):
            rig.save_cmd_lines()
        rig.stop()


main(shot)
