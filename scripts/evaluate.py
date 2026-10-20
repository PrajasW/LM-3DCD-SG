"""Score every results/<method>.jsonl against the same ground truth and write a comparison table.

A pair where a method declined to return a pose (success=false) or is missing counts as a failure.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import open3d as o3d
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lifelong.config import load_config  # noqa: E402
from lifelong.data import load_scan  # noqa: E402
from lifelong.metrics import RIO_THRESHOLDS, RR_RMSE, is_success, pose_errors  # noqa: E402
from lifelong.protocol import load_pairs  # noqa: E402
from lifelong.transforms import apply  # noqa: E402

PUBLISHED = """
Published numbers on the baselines' own protocol (SGAligner sub-scan pairs, not comparable 1:1 with the table above):

| Method | Setting | RRE (deg) | RTE (cm) | RR (%) |
|---|---|---|---|---|
| SGAligner (ICCV'23) | GT graphs, identity init | 1.012 | 1.67 | 99.40 |
| SG-PGM (CVPR'24) | GT graphs, random transform | 1.567 | 3.51 | 98.72 |
| SG-Reg (T-RO'25) | 3RScan-GT pairs | - | - | 82.0 (SG-PGM 79.4 on same) |
| SGAligner++ (2025) | no registration numbers, no code | - | - | - |
"""


def eval_points(root, pair, voxel):
    scan = load_scan(os.path.join(root, pair["rescan"]))
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(apply(pair["T_rand"], scan.points)))
    return np.asarray(pcd.voxel_down_sample(voxel).points)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--pairs", default=None)
    ap.add_argument("--results", default="results")
    ap.add_argument("--tag", default="", help="only score files named <method><tag>.jsonl")
    args = ap.parse_args()
    cfg = load_config(args.config)
    pairs = load_pairs(args.pairs or cfg["data"]["pairs"])
    pts = {(p["ref"], p["rescan"]): eval_points(cfg["data"]["root"], p, cfg["protocol"]["eval_voxel"]) for p in pairs}

    rows, summary = [], []
    for path in sorted(glob.glob(os.path.join(args.results, f"*{args.tag}.jsonl"))):
        method = os.path.basename(path)[: -len(f"{args.tag}.jsonl")]
        if not args.tag and method.endswith("_aligned"):
            continue
        recs = {}
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                recs[(r["ref"], r["rescan"])] = r
        for p in pairs:
            key = (p["ref"], p["rescan"])
            r = recs.get(key)
            row = {"method": method, "ref": p["ref"], "rescan": p["rescan"], "returned": bool(r and r["success"])}
            if r is not None:
                err = pose_errors(np.asarray(r["T_est"]), p["T_gt"], pts[key])
                row.update(err, time_s=r["time_s"])
                for k in ("static_precision", "static_recall", "n_static", "reason"):
                    if k in r:
                        row[k] = r[k]
            else:
                row.update(rre=np.inf, rte=np.inf, rmse=np.inf, time_s=np.nan)
            for t, a in RIO_THRESHOLDS:
                row[f"succ_{int(t * 100)}cm_{int(a)}deg"] = row["returned"] and is_success(row, t, a)
            row["rr"] = row["returned"] and row["rmse"] < RR_RMSE
            rows.append(row)

    df = pd.DataFrame(rows)
    os.makedirs(args.results, exist_ok=True)
    df.to_csv(os.path.join(args.results, f"per_pair{args.tag}.csv"), index=False)
    for method, g in df.groupby("method", sort=False):
        ok = g[g["returned"]]
        s = {"method": method, "pairs": len(g), "returned (%)": 100 * g["returned"].mean()}
        for t, a in RIO_THRESHOLDS:
            s[f"succ@{int(t * 100)}cm/{int(a)}° (%)"] = 100 * g[f"succ_{int(t * 100)}cm_{int(a)}deg"].mean()
        s["RR@0.2m (%)"] = 100 * g["rr"].mean()
        s["median RRE (°)"] = ok["rre"].median() if len(ok) else np.nan
        s["median RTE (cm)"] = 100 * ok["rte"].median() if len(ok) else np.nan
        s["mean time (s)"] = g["time_s"].mean()
        has_static = "static_precision" in g and g["static_precision"].notna().any()
        s["static P/R (%)"] = (f"{100 * g['static_precision'].mean():.1f}/{100 * g['static_recall'].mean():.1f}"
                               if has_static else "-")
        summary.append(s)
    table = pd.DataFrame(summary).to_markdown(index=False, floatfmt=".2f")
    out = os.path.join(args.results, f"two_visit_table{args.tag}.md")
    with open(out, "w") as f:
        f.write(f"# Two-visit relocalization ({len(pairs)} pairs)\n\n{table}\n{PUBLISHED}")
    print(table)
    print("->", out)


if __name__ == "__main__":
    main()
