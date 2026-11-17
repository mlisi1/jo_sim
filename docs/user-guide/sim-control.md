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

<figure class="jo-media">
<video src="../../assets/videos/sim_control.mp4" poster="../../assets/videos/sim_control.jpg" controls muted loop playsinline preload="none"></video>
<figcaption>Started with <code>--paused</code>: two steps of 150 iterations (Jo, spawned 0.6 m up, drops a
little at each), then play and pause. The RTF readout is at the bottom right of the Gazebo view.</figcaption>
</figure>

## Real-time factor

```bash
./jo sim --rtf 0.5         # half speed
./jo sim --rtf 0           # as fast as possible
```

`rtf:=X` sets the world's `<physics><real_time_factor>`. Empty means the world's own, usually 1.
Everything runs on sim time (`/clock`), so the stack follows the simulator at any speed.

