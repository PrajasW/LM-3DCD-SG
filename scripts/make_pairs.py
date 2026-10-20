"""Two-visit pairs (reference = map, rescan = new visit) with one fixed random SE(3) perturbation each.

The perturbation is stored so every method (ours and all baselines) sees exactly the same input.
Ground truth: T_gt (perturbed rescan -> reference) = T_rescan_to_ref @ inv(T_rand).

--aligned instead moves each rescan into its reference frame (T_rand = T_rescan_to_ref, so T_gt = I). This is the
setting the learned baselines were trained/evaluated in (sub-scans sharing one frame) and serves as a sanity check
of their adapters and as an upper bound for them.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lifelong.config import load_config  # noqa: E402
from lifelong.data import LABEL_PLY, Meta3RScan  # noqa: E402
from lifelong.transforms import inv, random_se3  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--aligned", action="store_true", help="rescan pre-aligned to the reference (T_gt = I)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    meta = Meta3RScan(cfg["data"]["meta"])
    root = cfg["data"]["root"]
    rng = np.random.default_rng(cfg["protocol"]["seed"])

    pairs = []
    for ref in sorted(os.listdir(root)):
        if ref not in meta.references or not os.path.exists(os.path.join(root, ref, LABEL_PLY)):
            continue
        for rescan in meta.rescans_of(ref):
            if not os.path.exists(os.path.join(root, rescan, LABEL_PLY)):
                continue
            if args.aligned:
                T_rand = meta.T_rescan_to_ref(rescan)
            else:
                T_rand = random_se3(rng, cfg["protocol"]["max_translation"])
            T_gt = meta.T_rescan_to_ref(rescan) @ inv(T_rand)
            ch = meta.changes(rescan)
            pairs.append({
                "ref": ref, "rescan": rescan,
                "T_rand": T_rand.tolist(), "T_gt": T_gt.tolist(),
                "changes": {k: sorted(v) for k, v in ch.items()},
            })
    out = args.out or (cfg["data"]["pairs"].replace(".json", "_aligned.json") if args.aligned else cfg["data"]["pairs"])
    with open(out, "w") as f:
        json.dump(pairs, f, indent=1)
    print(f"{len(pairs)} pairs -> {out}")


if __name__ == "__main__":
    main()
