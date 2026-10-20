"""Shared two-visit protocol I/O: load a pair as every method sees it, and write per-pair results."""
import json
import os
from dataclasses import replace

import numpy as np

from .data import load_scan
from .transforms import apply


def load_pairs(path):
    with open(path) as f:
        pairs = json.load(f)
    for p in pairs:
        p["T_rand"] = np.asarray(p["T_rand"])
        p["T_gt"] = np.asarray(p["T_gt"])
    return pairs


def load_pair_scans(pair, root, ssg=None):
    """Reference scan in its own frame and the rescan moved by the pair's random transform."""
    ref = load_scan(os.path.join(root, pair["ref"]), ssg)
    new = load_scan(os.path.join(root, pair["rescan"]), ssg)
    new = replace(new, points=apply(pair["T_rand"], new.points))
    return ref, new


class ResultWriter:
    """One JSON line per pair: {ref, rescan, T_est, success, time_s, extra}."""

    def __init__(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.f = open(path, "w")

    def write(self, pair, T_est, success, time_s, **extra):
        rec = {"ref": pair["ref"], "rescan": pair["rescan"], "T_est": np.asarray(T_est).tolist(),
               "success": bool(success), "time_s": float(time_s), **extra}
        self.f.write(json.dumps(rec) + "\n")
        self.f.flush()

    def close(self):
        self.f.close()
