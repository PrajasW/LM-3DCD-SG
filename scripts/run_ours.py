"""Run our relocalization (Steps 1-3) on every two-visit pair.

Writes results/ours.jsonl (with ICP refinement) and results/ours_centroid.jsonl (centroid-only ablation).
"""
import argparse
import os
import sys
import time

from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lifelong.config import load_config  # noqa: E402
from lifelong.data import SSG3D  # noqa: E402
from lifelong.graph import build_graph  # noqa: E402
from lifelong.metrics import static_set_scores  # noqa: E402
from lifelong.protocol import ResultWriter, load_pair_scans, load_pairs  # noqa: E402
from lifelong.relocalize import relocalize  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--pairs", default=None)
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--tag", default="", help="suffix for result files (e.g. _aligned)")
    args = ap.parse_args()
    cfg = load_config(args.config)
    pairs = load_pairs(args.pairs or cfg["data"]["pairs"])
    ssg = SSG3D(cfg["data"]["meta"])

    writers = {name: ResultWriter(os.path.join(args.out_dir, f"{name}{args.tag}.jsonl"))
               for name in ("ours", "ours_centroid")}
    for pair in tqdm(pairs, desc="ours"):
        ref, new = load_pair_scans(pair, cfg["data"]["root"], ssg)
        t = time.perf_counter()
        g_map = build_graph(ref, cfg["graph"]["min_points"])
        g_new = build_graph(new, cfg["graph"]["min_points"])
        t_graph = time.perf_counter() - t

        changed = set().union(*pair["changes"].values())
        gt_static = (set(g_map.objects) & set(g_new.objects)) - changed

        for name, refine in (("ours_centroid", False), ("ours", True)):
            res = relocalize(g_map, g_new, cfg, refine=refine)
            p, r = static_set_scores(res.static_pairs, gt_static)
            writers[name].write(
                pair, res.T, res.success, res.timings["total"],
                graph_time_s=t_graph, reason=res.reason, n_candidates=res.n_candidates,
                n_static=len(res.static_pairs), n_gt_static=len(gt_static),
                n_map_objects=len(g_map.objects), n_new_objects=len(g_new.objects),
                static_precision=p, static_recall=r, fitness=res.fitness, timings=res.timings,
                n_moved_groups=len(res.moved_groups),
            )
    for w in writers.values():
        w.close()


if __name__ == "__main__":
    main()
