"""Figures for the mid-submission report (report/figures/*.pdf), computed from data/ and results/.

  python scripts/make_figures.py
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lifelong.candidates import candidate_matches  # noqa: E402
from lifelong.config import load_config  # noqa: E402
from lifelong.consistency import compatibility_matrix, consistent_groups  # noqa: E402
from lifelong.data import SSG3D  # noqa: E402
from lifelong.graph import build_graph  # noqa: E402
from lifelong.metrics import pose_errors  # noqa: E402
from lifelong.protocol import load_pair_scans, load_pairs  # noqa: E402
from lifelong.relocalize import relocalize  # noqa: E402
from lifelong.transforms import apply  # noqa: E402

OUT = "report/figures"
# Fixed categorical order (validated reference palette, light mode); colour follows the method, never its rank.
METHODS = [  # key, label, colour
    ("ours", "Ours (Steps 1-3)", "#2a78d6"),
    ("fpfh_ransac", "FPFH + RANSAC", "#eb6834"),
    ("fpfh_teaser", "FPFH + TEASER++", "#1baf7a"),
    ("sgaligner", "SGAligner", "#eda100"),
    ("sgpgm", "SG-PGM", "#e87ba4"),
    ("ours_centroid", "Ours, centroid only", "#6250d6"),
]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(os.path.join(OUT, name))
    plt.close(fig)
    print("->", os.path.join(OUT, name))


def floor_frame(g):
    """2D top-down coordinates in the graph's own floor plane (so a randomly rotated scan is drawn upright)."""
    up = g.floor_normal
    e1 = np.cross(up, [1.0, 0, 0] if abs(up[0]) < 0.9 else [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    return lambda p: np.stack([p @ e1, p @ e2], -1)


def obj_colors(ids):
    cmap = plt.get_cmap("tab20")
    return {i: cmap(k % 20) for k, i in enumerate(sorted(ids))}


# Comparative and directional 3DSSG relations ("bigger than", "left", ...) link far-apart objects and clutter the
# drawing; only support / contact relations and our proximity edges are drawn.
DRAWN_RELATIONS = {"supported by", "standing on", "lying on", "hanging on", "attached to", "leaning against",
                   "connected to", "part of", "build in", "standing in", "lying in", "hanging in", "cover", "near"}


def draw_graph(ax, g, title, proj, colors, max_pts=30000, seed=0):
    rng = np.random.default_rng(seed)
    s = g.structure_points()
    if len(s):
        s = s[rng.choice(len(s), min(len(s), max_pts), replace=False)]
        ax.scatter(*proj(s).T, s=0.15, c="#cfcdc6", lw=0, rasterized=True)
    for i, o in g.objects.items():
        p = o.points[rng.choice(len(o.points), min(len(o.points), 1500), replace=False)]
        ax.scatter(*proj(p).T, s=0.3, color=colors[i], lw=0, rasterized=True)
    for a, b, rel in g.edges:
        if rel not in DRAWN_RELATIONS:
            continue
        ca, cb = proj(g.objects[a].centroid), proj(g.objects[b].centroid)
        ax.plot([ca[0], cb[0]], [ca[1], cb[1]], color=MUTED if rel != "near" else "#a8a69f",
                lw=0.5 if rel != "near" else 0.35, ls="-" if rel != "near" else ":", zorder=2)
    c = proj(np.stack([o.centroid for o in g.objects.values()]))
    ax.scatter(*c.T, s=9, color=INK, zorder=3, lw=0)
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.set_xticks([]), ax.set_yticks([])
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)


def fig_scene_graphs(cfg, pair):
    ref, new = load_pair_scans(pair, cfg["data"]["root"], SSG3D(cfg["data"]["meta"]))
    g1, g2 = build_graph(ref), build_graph(new)
    colors = obj_colors(set(g1.objects) | set(g2.objects))
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.7))
    draw_graph(axs[0], g1, f"Map: reference scan ({len(g1.objects)} objects)", floor_frame(g1), colors)
    draw_graph(axs[1], g2, f"New visit: rescan in an unknown frame ({len(g2.objects)} objects)",
               floor_frame(g2), colors)
    axs[1].plot([], [], color=MUTED, lw=0.6, label="3DSSG support relation")
    axs[1].plot([], [], color="#a8a69f", lw=0.5, ls=":", label="proximity edge")
    axs[1].scatter([], [], s=9, color=INK, label="object node (centroid)")
    axs[1].scatter([], [], s=9, color="#cfcdc6", label="floor / wall / ceiling")
    axs[1].legend(loc="lower right", frameon=False, markerscale=1.2, bbox_to_anchor=(1.0, -0.12), ncol=2)
    save(fig, "scene_graphs.pdf")
    return g1, g2


def fig_relocalization(cfg, g1, g2, pair):
    res = relocalize(g1, g2, cfg)
    err = pose_errors(res.T, pair["T_gt"])
    proj = floor_frame(g1)
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(3.4, 2.9))
    s = np.concatenate([o.points for o in g1.objects.values()] + [g1.structure_points()])
    s = s[rng.choice(len(s), 40000, replace=False)]
    ax.scatter(*proj(s).T, s=0.15, c="#cfcdc6", lw=0, rasterized=True)
    static = dict(res.static_pairs)
    moved = {i: k for k, grp in enumerate(res.moved_groups) for i, _ in grp}
    for j, o in g2.objects.items():
        p = apply(res.T, o.points[rng.choice(len(o.points), min(len(o.points), 1200), replace=False)])
        col = "#2a78d6" if j in static.values() else ("#eb6834" if j in {b for grp in res.moved_groups for _, b in grp}
                                                      else "#8a887f")
        ax.scatter(*proj(p).T, s=0.35, color=col, lw=0, rasterized=True)
    for i, j in res.static_pairs:
        a, b = proj(g1.objects[i].centroid), proj(apply(res.T, g2.objects[j].centroid[None])[0])
        ax.plot([a[0], b[0]], [a[1], b[1]], color=INK, lw=0.6)
        ax.scatter(*a, s=7, color=INK, lw=0, zorder=3)
    for grp in res.moved_groups:
        for i, j in grp:
            a, b = proj(g1.objects[i].centroid), proj(apply(res.T, g2.objects[j].centroid[None])[0])
            ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9, mutation_scale=7), zorder=4)
    ax.scatter([], [], s=9, color="#2a78d6", label=f"static set ({len(res.static_pairs)} objects)")
    ax.scatter([], [], s=9, color="#eb6834", label=f"other consistent groups ({sum(map(len, res.moved_groups))} objects)")
    ax.scatter([], [], s=9, color="#8a887f", label="unmatched")
    ax.scatter([], [], s=9, color="#cfcdc6", label="map")
    ax.legend(loc="upper center", frameon=False, fontsize=6.5, bbox_to_anchor=(0.5, 0.0), ncol=2)
    ax.set_title(f"New visit placed in the map: RRE {err['rre']:.1f}°, RTE {100 * err['rte']:.1f} cm")
    ax.set_aspect("equal"), ax.set_xticks([]), ax.set_yticks([]), ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    save(fig, "relocalization.pdf")


def fig_consistency(cfg, pairs):
    """Distance residuals |d_map - d_new| / tolerance for candidate-match pairs, split by ground truth."""
    good, bad = [], []
    for p in pairs:
        ref, new = load_pair_scans(p, cfg["data"]["root"])
        g1, g2 = build_graph(ref), build_graph(new)
        cands = candidate_matches(g1, g2, cfg["candidates"])
        changed = set().union(*p["changes"].values())
        c1 = np.stack([g1.objects[c.map_id].centroid for c in cands])
        c2 = np.stack([g2.objects[c.new_id].centroid for c in cands])
        r = np.array([max(g1.objects[c.map_id].radius, g2.objects[c.new_id].radius) for c in cands])
        d1 = np.linalg.norm(c1[:, None] - c1[None], axis=-1)
        d2 = np.linalg.norm(c2[:, None] - c2[None], axis=-1)
        tol = cfg["consistency"]["dist_eps"] + cfg["consistency"]["radius_beta"] * (r[:, None] + r[None])
        q = np.abs(d1 - d2) / tol
        ok = np.array([c.map_id == c.new_id and c.map_id not in changed for c in cands])
        iu = np.triu_indices(len(cands), 1)
        m = ok[:, None] & ok[None]
        mid = np.array([c.map_id for c in cands]); nid = np.array([c.new_id for c in cands])
        distinct = (mid[:, None] != mid[None]) & (nid[:, None] != nid[None])
        good.append(q[iu][m[iu] & distinct[iu]])
        bad.append(q[iu][~m[iu] & distinct[iu]])
    good, bad = np.concatenate(good), np.concatenate(bad)
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    bins = np.logspace(-2.5, 2.5, 41)
    ax.hist(bad, bins=bins, weights=np.full(len(bad), 100 / len(bad)), color="#eb6834", alpha=0.8,
            label=f"involves a wrong or moved match (n={len(bad)})", edgecolor="white", lw=0.3)
    ax.hist(good, bins=bins, weights=np.full(len(good), 100 / len(good)), color="#2a78d6", alpha=0.8,
            label=f"both matches correct and static (n={len(good)})", edgecolor="white", lw=0.3)
    ax.axvline(1.0, color=INK, lw=0.8, ls="--")
    for txt, dx, ha in (("accept", -3, "right"), ("reject", 3, "left")):
        ax.annotate(txt, xy=(1.0, 0.97), xycoords=("data", "axes fraction"), xytext=(dx, 0),
                    textcoords="offset points", ha=ha, va="top", fontsize=6.3, color=INK)
    ax.set_xscale("log")
    ax.set_xlabel(r"normalised distance residual $|d^{\mathrm{map}}_{ab}-d^{\mathrm{new}}_{ab}|\,/\,\tau_{ab}$")
    ax.set_ylabel("share of match pairs (%)")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=6.3, ncol=1)
    save(fig, "consistency.pdf")
    print(f"   accepted: correct {np.mean(good <= 1):.3f}, wrong {np.mean(bad <= 1):.3f}")


def fig_success_curves():
    fig, axs = plt.subplots(1, 2, figsize=(4.75, 2.3), sharey=True)
    taus = np.linspace(0, 0.5, 101)
    for ax, tag, title in ((axs[0], "", "Random rigid transform"),
                           (axs[1], "_aligned", "Rescan pre-aligned")):
        d = pd.read_csv(f"results/per_pair{tag}.csv")
        for key, label, col in METHODS:  # ours is drawn on top (it coincides with TEASER++ on this subset)
            g = d[d.method == key]
            if g.empty:
                continue
            ok = [100 * np.mean(g.returned & (g.rte <= t) & (g.rre <= 100 * t)) for t in taus]
            ax.plot(100 * taus, ok, color=col, lw=2.4 if key == "ours" else 1.1, zorder={"ours": 4, "fpfh_teaser": 5}.get(key, 3),
                    ls="--" if key == "ours_centroid" else ((0, (4, 2)) if key == "fpfh_teaser" else "-"),
                    label=label)
        for t in (10, 20):
            ax.axvline(t, color=GRID, lw=0.8, zorder=0)
        ax.set_title(title)
        ax.set_xlabel(r"threshold $\tau$ ($\tau$ cm and $\tau^\circ$)")
        ax.set_xlim(0, 50), ax.set_ylim(0, 100)
    axs[0].set_ylabel("pairs relocalized (%)")
    axs[1].legend(frameon=False, loc="lower right", ncol=1, fontsize=6.3)
    save(fig, "success_curves.pdf")


def fig_runtime():
    d = pd.read_csv("results/per_pair.csv")
    fig, ax = plt.subplots(figsize=(2.6, 2.3))
    for key, label, col in METHODS:
        g = d[d.method == key]
        if g.empty:
            continue
        x, y = max(g.time_s.mean(), 1e-3), 100 * g.succ_20cm_20deg.mean()
        ax.scatter(x, y, s=34, color=col, edgecolor="white", lw=1.2, zorder=3)
        off = {"ours": (-6, 6, "right"), "fpfh_teaser": (4, -10, "left"), "fpfh_ransac": (-5, 5, "right"),
               "ours_centroid": (0, -11, "left")}.get(key, (5, -2, "left"))
        ax.annotate(label, (x, y), xytext=off[:2], textcoords="offset points", ha=off[2], fontsize=6.5, color=INK)
    ax.set_xscale("log")
    ax.set_xlabel("mean pose time per pair (s)")
    ax.set_ylabel("succ. @ 20 cm / 20° (%)")
    ax.set_ylim(0, 100), ax.set_xlim(5e-4, 30)
    save(fig, "runtime.pdf")


def fig_per_pair():
    d = pd.read_csv("results/per_pair.csv")
    keys = [k for k, _, _ in METHODS]
    t = d.pivot_table(index="rescan", columns="method", values="succ_20cm_20deg", aggfunc="first")[keys]
    ref = d.drop_duplicates("rescan").set_index("rescan")["ref"]
    t = t.loc[sorted(t.index, key=lambda r: (ref[r], r))]
    status = t.astype(float).values.copy()
    ret = d.pivot_table(index="rescan", columns="method", values="returned", aggfunc="first")[keys].loc[t.index]
    status[(~ret.values.astype(bool))] = 0.5  # declined
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    from matplotlib.colors import ListedColormap
    ax.imshow(status, cmap=ListedColormap(["#eb6834", "#d9d7cf", "#2a78d6"]), vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(keys)), [lab for _, lab, _ in METHODS], rotation=35, ha="right")
    ax.set_yticks(range(len(t)), [f"{ref[r][:8]} / {r[:8]}" for r in t.index], fontsize=5.5)
    ax.set_xticks(np.arange(-.5, len(keys)), minor=True), ax.set_yticks(np.arange(-.5, len(t)), minor=True)
    ax.grid(which="minor", color="white", lw=1.2), ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    for lab, col in (("success", "#2a78d6"), ("wrong pose", "#eb6834"), ("declined", "#d9d7cf")):
        ax.scatter([], [], marker="s", s=20, color=col, label=lab)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=3, fontsize=6.3)
    ax.set_ylabel("reference / rescan")
    save(fig, "per_pair.pdf")


def main():
    cfg = load_config("configs/default.yaml")
    pairs = load_pairs(cfg["data"]["pairs"])
    pair = next(p for p in pairs if p["rescan"].startswith("9766cbe5"))
    g1, g2 = fig_scene_graphs(cfg, pair)
    fig_relocalization(cfg, g1, g2, pair)
    fig_consistency(cfg, pairs)
    fig_success_curves()
    fig_runtime()
    fig_per_pair()
    with open(os.path.join(OUT, "stats.json"), "w") as f:
        json.dump({"pair": pair["rescan"], "ref": pair["ref"]}, f)


if __name__ == "__main__":
    main()
