"""Loading 3RScan scans/metadata and 3DSSG annotations."""
import json
import os
from dataclasses import dataclass, field

import numpy as np
from plyfile import PlyData

LABEL_PLY = "labels.instances.annotated.v2.ply"
SEMSEG = "semseg.v2.json"


@dataclass
class Scan:
    scan_id: str
    points: np.ndarray          # (N, 3) mesh vertices, scan's own frame
    colors: np.ndarray          # (N, 3) uint8
    object_ids: np.ndarray      # (N,) instance id per vertex, 0 = unlabelled
    labels: dict                # instance id -> class label (str)
    relationships: list = field(default_factory=list)  # 3DSSG [(subj, obj, rel_name)]


def _T_from_list(values):
    # 3RScan stores 4x4 matrices as column-major 16-lists.
    return np.asarray(values, dtype=float).reshape(4, 4).T


class Meta3RScan:
    """Index over 3RScan.json: which rescans belong to which reference, GT alignments and changes."""

    def __init__(self, meta_dir):
        with open(os.path.join(meta_dir, "3RScan.json")) as f:
            entries = json.load(f)
        self.references = {}
        self.rescans = {}
        for e in entries:
            self.references[e["reference"]] = e
            for s in e["scans"]:
                self.rescans[s["reference"]] = (e["reference"], s)

    def split(self, ref_id):
        return self.references[ref_id]["type"]

    def rescans_of(self, ref_id):
        return [s["reference"] for s in self.references[ref_id]["scans"]]

    def T_rescan_to_ref(self, rescan_id):
        _, s = self.rescans[rescan_id]
        if "transform" not in s:
            raise KeyError(f"no ground-truth transform for {rescan_id} (test split?)")
        return _T_from_list(s["transform"])

    def changes(self, rescan_id):
        """Instance ids that moved rigidly, deformed, or were removed between reference and rescan."""
        _, s = self.rescans[rescan_id]
        return {
            "rigid": {r["instance_reference"] for r in s.get("rigid", [])},
            "nonrigid": set(s.get("nonrigid", [])),
            "removed": set(s.get("removed", [])),
        }


def load_scan(scan_dir, ssg=None):
    """Read the annotated instance PLY and semseg labels of one scan."""
    scan_id = os.path.basename(os.path.normpath(scan_dir))
    v = PlyData.read(os.path.join(scan_dir, LABEL_PLY))["vertex"].data
    points = np.stack([v["x"], v["y"], v["z"]], axis=1).astype(np.float64)
    colors = np.stack([v["red"], v["green"], v["blue"]], axis=1)
    object_ids = np.asarray(v["objectId"], dtype=np.int64)

    with open(os.path.join(scan_dir, SEMSEG)) as f:
        groups = json.load(f)["segGroups"]
    labels = {int(g["objectId"]): g["label"] for g in groups}

    relationships = []
    if ssg is not None and scan_id in ssg.relationships:
        relationships = ssg.relationships[scan_id]
    return Scan(scan_id, points, colors, object_ids, labels, relationships)


class SSG3D:
    """3DSSG objects.json / relationships.json (optional; only used for graph edges and attributes)."""

    def __init__(self, ssg_dir):
        self.objects, self.relationships = {}, {}
        obj_path = os.path.join(ssg_dir, "objects.json")
        rel_path = os.path.join(ssg_dir, "relationships.json")
        if os.path.exists(obj_path):
            with open(obj_path) as f:
                for s in json.load(f)["scans"]:
                    self.objects[s["scan"]] = {int(o["id"]): o for o in s["objects"]}
        if os.path.exists(rel_path):
            with open(rel_path) as f:
                for s in json.load(f)["scans"]:
                    self.relationships[s["scan"]] = [(int(a), int(b), name) for a, b, _, name in s["relationships"]]
