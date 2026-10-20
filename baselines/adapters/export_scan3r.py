"""Export our two-visit pairs into the SGAligner/SG-PGM 3RScan data layout.

Produces <out>/ (an SGAligner "Scan3R" root, scan_type='scan'):
  scans/<id>/data.npy           structured vertex array (x, y, z, rgb, objectId, globalId, NYU40, Eigen13, RIO27)
  files/{3RScan.json, relationships.txt, classes.txt, attributes.txt, obj_attr.pkl}
  files/{objects.json, relationships.json}  3DSSG entries of the exported scans
  files/val_scans.txt, files/anchors_val.json

The new visit of each pair is written as "<rescan>_rand": the rescan moved by the pair's stored random transform,
i.e. exactly the input our method sees. The reference scan keeps its own frame. SGAligner's own
preprocessing/scan3r/preprocess.py is then run on this root to build the per-scan pickles both baselines consume.
"""
import argparse
import json
import os
import shutil
import sys

import numpy as np
from plyfile import PlyData

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from lifelong.data import LABEL_PLY  # noqa: E402
from lifelong.protocol import load_pairs  # noqa: E402
from lifelong.transforms import apply  # noqa: E402

VERTEX_DTYPE = [("x", "f4"), ("y", "f4"), ("z", "f4"), ("red", "u1"), ("green", "u1"), ("blue", "u1"),
                ("objectId", "h"), ("globalId", "h"), ("NYU40", "u1"), ("Eigen13", "u1"), ("RIO27", "u1")]
META_FROM_WEIGHTS = ["relationships.txt", "classes.txt", "attributes.txt", "obj_attr.pkl"]
# SGAligner's preprocessing asserts that no 'inside' relation remains (it was excluded from their training data).
DROPPED_RELATIONS = {"inside"}


def new_visit_id(rescan_id):
    return f"{rescan_id}_rand"


def write_vertices(ply_path, out_path, T=None):
    v = PlyData.read(ply_path)["vertex"].data
    out = np.empty(len(v), dtype=VERTEX_DTYPE)
    for name, _ in VERTEX_DTYPE:
        out[name] = v[name]
    if T is not None:
        xyz = apply(T, np.stack([v["x"], v["y"], v["z"]], 1).astype(np.float64))
        out["x"], out["y"], out["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.save(out_path, out)
    return np.unique(out["objectId"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=os.path.join(ROOT, "data/pairs_val.json"))
    ap.add_argument("--scans", default=os.path.join(ROOT, "data/3RScan"))
    ap.add_argument("--meta", default=os.path.join(ROOT, "data/meta"))
    ap.add_argument("--weights", default=os.path.join(ROOT, "baselines/weights/sgaligner"))
    ap.add_argument("--out", default=os.path.join(ROOT, "baselines/work/Scan3R"))
    args = ap.parse_args()

    pairs = load_pairs(args.pairs)
    files = os.path.join(args.out, "files")
    os.makedirs(files, exist_ok=True)
    shutil.copy(os.path.join(args.meta, "3RScan.json"), files)
    for fn in META_FROM_WEIGHTS:
        shutil.copy(os.path.join(args.weights, fn), files)

    objects = {s["scan"]: s for s in json.load(open(os.path.join(args.meta, "objects.json")))["scans"]}
    rels = {s["scan"]: s for s in json.load(open(os.path.join(args.meta, "relationships.json")))["scans"]}

    scan_ids, anchors, out_obj, out_rel = [], [], [], []

    def add_scan(src_id, out_id, T=None):
        ids = write_vertices(os.path.join(args.scans, src_id, LABEL_PLY),
                             os.path.join(args.out, "scans", out_id, "data.npy"), T)
        o = dict(objects[src_id], scan=out_id)
        r = dict(rels[src_id], scan=out_id)
        r["relationships"] = [t for t in r["relationships"] if t[3] not in DROPPED_RELATIONS]
        out_obj.append(o)
        out_rel.append(r)
        scan_ids.append(out_id)
        return set(int(i) for i in ids if i != 0)

    exported_refs = {}
    for p in pairs:
        if p["ref"] not in exported_refs:
            exported_refs[p["ref"]] = add_scan(p["ref"], p["ref"])
        new_ids = add_scan(p["rescan"], new_visit_id(p["rescan"]), p["T_rand"])
        shared = sorted(exported_refs[p["ref"]] & new_ids)
        anchors.append({"src": new_visit_id(p["rescan"]), "ref": p["ref"], "overlap": 1.0, "anchorIds": shared})

    json.dump({"scans": out_obj}, open(os.path.join(files, "objects.json"), "w"))
    json.dump({"scans": out_rel}, open(os.path.join(files, "relationships.json"), "w"))
    np.savetxt(os.path.join(files, "val_scans.txt"), np.array(scan_ids), fmt="%s")
    json.dump(anchors, open(os.path.join(files, "anchors_val.json"), "w"))
    print(f"exported {len(scan_ids)} scans / {len(anchors)} pairs -> {args.out}")


if __name__ == "__main__":
    main()
