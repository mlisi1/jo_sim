# Troubleshooting

??? failure "`rmw_create_node: failed to create domain`"
    CycloneDDS's default limit is 32 participants per domain, too few for the full GPS stack. The
    container's `docker/utils/cyclonedds.xml` raises it to 100. If you use your own
    `CYCLONEDDS_URI`, raise the limit there too.

??? failure "The DendROS TUI does not start; I get plain coloured output"
    The terminal reports 8 colours: `docker exec -it` sets `TERM=xterm`. Use `./jo`, which passes
    your `TERM`, or run `docker exec -it -e TERM=$TERM ...`.

??? failure "A closed terminal left the simulation running"
    Run `./jo stop` (add `--domain` and `--partition` if you started it with them).

??? failure "RTF far below 1"
    Another GPU or CPU heavy job is running (check `nvidia-smi`, `uptime`), or the world is heavy
    (check `check_worlds`).

??? failure "Big worlds: nothing on sim time starts"
    Fixed: the clock is bridged from the world's own clock topic, not the root `/clock`. If you
    write your own bridge, do the same (see [Design decisions](../developer/decisions.md)).

??? failure "Lag on an external monitor"
    On laptops with reverse PRIME (HDMI on the NVIDIA GPU, desktop on the Intel one), the external
    monitor can lag. The cause is the display setup, not the simulator.

!!! planned "Planned content"
    More entries, collected from the project notes.
