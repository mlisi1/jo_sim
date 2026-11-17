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
<video src="../../assets/videos/sim_control.mp4" poster="../../assets/videos/sim_control.jpg" autoplay muted loop playsinline></video>
<figcaption>Jo driving forward on <code>/cmd_vel</code>: pause freezes it mid-motion, each
<code>step 500</code> advances half a second of sim time (500 iterations at the 1 ms physics step),
play lets it drive on. The terminal shows the commands' real output.</figcaption>
</figure>

## Real-time factor

```bash
./jo sim --rtf 0.5         # half speed
./jo sim --rtf 0           # as fast as possible
```

`rtf:=X` sets the world's `<physics><real_time_factor>`. Empty means the world's own, usually 1.
Everything runs on sim time (`/clock`), so the stack follows the simulator at any speed.

