#!/usr/bin/env python3
"""Measures the simulator's cost per sensor and per stack mode, for docs/user-guide/performance.md.

Starts sim_bringup headless in the container once per configuration (docs/gen/perf_probe.py, fed on
stdin) and prints a markdown table: real-time factor, CPU cores and GPU memory. About 12 minutes,
and it needs the GPU: run it on a free machine, from the repository root, with the container up:

    python3 docs/gen/measure_performance.py [--domain 79] [--partition jo_sim_docs] [--world office_cpr]

The numbers depend on the machine, so the table is pasted into the page with the machine and date,
not included as a generated file.
"""
import argparse, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTAINER = 'jo_sim-jo-sim-1'


def table(lines):
    head, rows = lines[0], lines[1:]
    out = [f"World `{head['world']}`, headless, settle {head['settle_s']:g} s, window {head['window_s']:g} s. "
           f"Idle GPU memory {head['idle_gpu_mem_mib']:g} MiB.\n",
           '| Configuration | RTF | CPU cores | GPU memory [GiB] |', '|---|---|---|---|']
    for r in rows:
        if 'error' in r:
            out.append(f"| {r['name']} | {r['error']} | | |")
            continue
        rtf = '—' if r['rtf'] is None else f"{r['rtf']:.2f}"
        out.append(f"| {r['name']} | {rtf} | {r['cpu_cores']:.1f} | {r['gpu_mem_mib'] / 1024:.1f} |")
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--domain', type=int, default=79)
    ap.add_argument('--partition', default='jo_sim_docs')
    ap.add_argument('--world', default='office_cpr')
    ap.add_argument('--jsonl', help='render a saved probe output instead of measuring')
    a = ap.parse_args()
    if a.jsonl:
        text = open(a.jsonl).read()
    else:
        cmd = ('source /opt/ros/jazzy/setup.bash; source /home/ros/install/setup.bash; '
               'python3 -; rc=$?; ros2 daemon stop >/dev/null 2>&1; exit $rc')
        with open(ROOT / 'docs' / 'gen' / 'perf_probe.py') as f:
            text = subprocess.run(['docker', 'exec', '-i', '-e', f'ROS_DOMAIN_ID={a.domain}',
                                   '-e', f'GZ_PARTITION={a.partition}', '-e', f'PERF_WORLD={a.world}',
                                   CONTAINER, 'bash', '-c', cmd], stdin=f, stdout=subprocess.PIPE,
                                  check=True, text=True).stdout
    print(table([json.loads(l) for l in text.splitlines() if l.strip()]))


if __name__ == '__main__':
    sys.exit(main())
