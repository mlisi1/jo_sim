# Simulation control

## Pause, play, step

```bash
./jo sim --paused          # or paused:=true
./jo ctl play              # or the play button in the Gazebo GUI
./jo ctl pause
./jo ctl step 100          # 100 physics steps, then paused
./jo ctl status
```

Inside the container, `sim_control play | pause | step [N] | status` does the same. It finds the
world's control service in the current `GZ_PARTITION`.

## Real-time factor

```bash
./jo sim --rtf 0.5         # half speed
./jo sim --rtf 0           # as fast as possible
```

`rtf:=X` sets the world's `<physics><real_time_factor>`. Empty means the world's own, usually 1.
Everything runs on sim time (`/clock`), so the stack follows the simulator at any speed.

<div class="media-ph" data-kind="video" markdown>
<span class="media-ph-kind">Video</span>
<p>Start paused, step, play, then RTF 0.5 vs 0 (the Gazebo RTF readout).</p>
</div>
