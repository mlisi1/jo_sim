# Contributing

- **Branches:** work on `dev` in every repository. After a clone the submodules are on a detached
  HEAD: run `git -C jo_description switch dev` (and the same for `jo_navigation`) before committing.
- **Commits:** few, grouped by topic, one per repository. Commit the submodule first, then
  jo_sim with the pointer bump.
- **Push order:** jo_description, jo_navigation, then jo_sim.
- **Docs in the same commit as the feature.** A new argument, topic, world feature or config
  difference updates its page here. `mkdocs build --strict` runs in CI.
- **Test in the sandbox** (domain 77, partition `jo_sim_test`). See [Testing](testing.md).

## Working on these docs

```bash
python3 -m venv .venv && .venv/bin/pip install -r docs/requirements.txt
.venv/bin/mkdocs serve          # http://127.0.0.1:8000, live reload
.venv/bin/mkdocs build --strict # what CI runs
```

- Pages are in `docs/`; the navigation is in `mkdocs.yml`.
- Media placeholders are `<div class="media-ph" data-kind="image|video|diagram">` blocks. Replace
  them with real media in `docs/assets/`. Keep videos short and compressed: Pages serves no Git LFS.
- Tooltips for abbreviations come from `docs/includes/abbreviations.md`.
- **Generated tables** (launch arguments, bridged topics, `./jo help`) live in
  `docs/includes/generated/`, and the pages include them. Don't edit them by hand: with the container
  up, run `python3 docs/gen/gen_tables.py` and commit the result. The generators find this
  checkout's container by themselves (`JO_CONTAINER` overrides it). The media scripts expect
  `jo_sim-jo-sim-1`, that is a clone in a folder named `jo_sim`. Do it whenever a launch argument,
  a bridge config or `./jo` changes.
- **Measured tables** (every topic with its rate and QoS, the TF tree, the node parameters) come from
  `python3 docs/gen/gen_topics.py`. It starts a headless simulator on domain 79, so it needs the GPU
  (about two minutes). Run it when a topic, a frame, a rate or a node parameter changes.
- **The performance table** comes from `python3 docs/gen/measure_performance.py` (about 12 minutes,
  GPU). It depends on the machine, so paste it into the page with the machine and the date.
- **The logo and home render** come from `docs/gen/render_logo/render.sh` (CPU only).
- **The world catalogue** (thumbnails and table) comes from `python3 docs/gen/gen_world_catalogue.py`
  (GPU, about a minute per world). Each world loads headless without the robot. A top-down depth pass
  finds the extent of what stands on the ground, then a 3/4 view frames it. Odd worlds get an
  override (azimuth, elevation, zoom) in `VIEWS`.
- **The videos** are rendered off-screen, so nothing opens on your monitors. They are made in two steps:
    1. `python3 docs/gen/media/shoot.py SHOT` runs `docs/gen/media/shots/SHOT.py` in the container,
       on domain 79 and Gazebo partition `jo_sim_docs`. The rig (`rig.py`) pauses the world and steps
       it one video frame at a time. A camera sensor renders each frame, and RViz or the GLIM viewer
       run on a virtual display (Xvfb `:99`). The frames go to `~/.cache/jo_sim_media/rig/SHOT`.
    2. `python3 docs/gen/media/videos.py NAME` composes the shots (cards, captions, splits, a
       picture in picture, the real terminal output) with `compose.py`, then writes
       `docs/assets/videos/NAME.mp4` and its poster. Add `--preview` for a contact sheet.

    A shot takes 5 to 30 minutes, depending on the stack it runs; composing takes about a minute.
    The `rtabmap` shot needs the image built with `BUILD_RTABMAP=true`: start a container of it, set
    `JO_MEDIA_CONTAINER` to its name, and start a second virtual display for `rtabmap_viz`
    (`Xvfb :98 -screen 0 1600x1000x24`).
    The ground truth page's plot comes from the glim_city shot:
    `python3 docs/gen/media/plot_ground_truth.py`.
    `shots_basic.sh` (the annotated Gazebo and RViz screenshots) is the exception: it opens real
    windows on a monitor.
