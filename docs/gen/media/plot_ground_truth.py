#!/usr/bin/env python3
"""The ground truth page's plot, from the glim_city shot (shots/glim_city.py records the ground
truth, GLIM's odometry and the EKF output in every frame).

    python3 docs/gen/media/plot_ground_truth.py

Left: the trajectories, top-down, in GLIM's map frame (origin and heading at the spawn pose).
Right: the position error of GLIM and of the EKF against the ground truth, over sim time.
Writes docs/assets/images/ground_truth_{light,dark}.png (the page shows one per colour scheme).
The ground truth is taken relative to the spawn pose (x 0, y 0, yaw pi in small_city), as the
page explains: GLIM's map and odom frames start there (glim_anchor_frame base)."""
import json
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
RIG = Path(os.environ.get('JO_MEDIA_RIG', Path.home() / '.cache/jo_sim_media/rig'))
SPAWN = (0.0, 0.0, math.pi)      # the shot's spawn pose (world x, y, yaw)

# validated with the dataviz validator: light on #fcfcfb, dark on the docs' navy #0b1220
THEMES = {
    'light': dict(surface='#fcfcfb', ink='#1f2937', muted='#6b7280', grid='#e5e7eb',
                  glim='#2a78d6', ekf='#eb6834', truth='#1f2937'),
    'dark': dict(surface='#0b1220', ink='#e2e8f0', muted='#94a3b8', grid='#1c2740',
                 glim='#3987e5', ekf='#d95926', truth='#e2e8f0'),
}


def load():
    """Unique messages per source (by stamp); the ground truth interpolated at each GLIM and EKF
    stamp, so a message is compared with where Jo was when it was stamped, not when it arrived."""
    recs = [json.loads(l) for l in open(RIG / 'glim_city' / 'frames.jsonl')]

    def series(key):
        seen, out = set(), []
        for r in recs:
            v = r.get(key)
            if v and len(v) > 5 and v[5] not in seen:
                seen.add(v[5])
                out.append((v[5], v[0], v[1]))
        return sorted(out)
    x0, y0, yaw0 = SPAWN
    c, s_ = math.cos(-yaw0), math.sin(-yaw0)
    gt = [(t, c * (x - x0) - s_ * (y - y0), s_ * (x - x0) + c * (y - y0)) for t, x, y in series('gt')]

    def gt_at(t):
        for (ta, xa, ya), (tb, xb, yb) in zip(gt, gt[1:]):
            if ta <= t <= tb:
                u = (t - ta) / (tb - ta) if tb > ta else 0.0
                return xa + u * (xb - xa), ya + u * (yb - ya)
        return None

    def compared(key):
        out = []
        for t, x, y in series(key):
            g = gt_at(t)
            if g:
                out.append((t, (x, y), g))
        return out
    return gt, compared('glim_global'), compared('ekf')


def err(a, b):
    return [math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(a, b)]


def plot(theme, gt, glim, ekf):
    th = THEMES[theme]
    for f in ('Inter', 'Inter Display'):
        if any(f == x.name for x in font_manager.fontManager.ttflist):
            plt.rcParams['font.family'] = f
            break
    plt.rcParams.update({'font.size': 13, 'axes.edgecolor': th['grid'], 'axes.labelcolor': th['muted'],
                         'xtick.color': th['muted'], 'ytick.color': th['muted'], 'text.color': th['ink']})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.6), dpi=110,
                                   gridspec_kw={'width_ratios': [1, 1.35], 'wspace': 0.22})
    fig.patch.set_facecolor(th['surface'])
    for ax in (ax1, ax2):
        ax.set_facecolor(th['surface'])
        ax.grid(True, color=th['grid'], linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)

    # trajectories: map frame, x forward from the spawn; drawn with west up (Jo drives up, then turns right, north)
    def xy(p):
        return [-q[1] for q in p], [q[0] for q in p]
    ax1.plot(*xy([(x, y) for _, x, y in gt]), color=th['truth'], lw=2, ls=(0, (4, 3)), label='Ground truth')
    ax1.plot(*xy([p for _, p, _ in glim]), color=th['glim'], lw=2, label='GLIM')
    ax1.plot(*xy([p for _, p, _ in ekf]), color=th['ekf'], lw=2, label='EKF')
    ax1.plot(0, 0, 'o', ms=8, color=th['ink'], mec=th['surface'], mew=2)
    ax1.annotate('spawn', (0, 0), (8, -4), textcoords='offset points', color=th['muted'], fontsize=12)
    ax1.set_aspect('equal', adjustable='datalim')
    ax1.set_xlabel('−y in the map frame (m)')
    ax1.set_ylabel('x in the map frame (m)')
    ax1.set_title('Trajectory', loc='left', fontsize=15, fontweight='bold', color=th['ink'])

    t0 = gt[0][0]
    tg, eg = [t - t0 for t, _, _ in glim], err([p for _, p, _ in glim], [g for _, _, g in glim])
    te, ee = [t - t0 for t, _, _ in ekf], err([p for _, p, _ in ekf], [g for _, _, g in ekf])
    ax2.plot(tg, eg, color=th['glim'], lw=2, label='GLIM')
    ax2.plot(te, ee, color=th['ekf'], lw=2, label='EKF')
    for ts, series, name, col in ((tg, eg, 'GLIM', th['glim']), (te, ee, 'EKF', th['ekf'])):
        ax2.plot(ts[-1], series[-1], 'o', ms=8, color=col, mec=th['surface'], mew=2)
        ax2.annotate(f'{name} {series[-1] * 100:.1f} cm', (ts[-1], series[-1]), (10, 0),
                     textcoords='offset points', va='center', color=th['ink'], fontsize=12)
    ts = tg
    ax2.set_xlim(0, max(tg[-1], te[-1]) * 1.18)
    ax2.set_ylim(0, max(max(eg), max(ee)) * 1.25 or 0.1)
    ax2.set_xlabel('sim time from the first recorded sample (s)')
    ax2.set_ylabel('position error (m)')
    ax2.set_title('Position error against the ground truth', loc='left', fontsize=15,
                  fontweight='bold', color=th['ink'])

    leg = fig.legend(*ax1.get_legend_handles_labels(), loc='upper center', ncol=3, frameon=False,
                     bbox_to_anchor=(0.5, 1.0), fontsize=13)
    for txt in leg.get_texts():
        txt.set_color(th['ink'])
    fig.subplots_adjust(top=0.84, bottom=0.12, left=0.06, right=0.98)
    out = ROOT / 'docs' / 'assets' / 'images' / f'ground_truth_{theme}.png'
    fig.savefig(out, facecolor=th['surface'])
    plt.close(fig)
    print(out, f'GLIM max {max(eg):.3f} final {eg[-1]:.3f} m; EKF max {max(ee):.3f} final {ee[-1]:.3f} m;',
          f'{len(eg)} GLIM and {len(ee)} EKF samples, {ts[-1]:.1f} s')


if __name__ == '__main__':
    data = load()
    for theme in THEMES:
        plot(theme, *data)
