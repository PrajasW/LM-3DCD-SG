"""Step 1: candidate matches from pose-invariant object descriptors (class, size/shape, height above floor)."""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Candidate:
    map_id: int
    new_id: int
    cost: float


def descriptor_cost(a, b, cfg):
    """Dissimilarity of two ObjectNodes; inf if they cannot be the same object."""
    if cfg["require_same_class"] and a.label != b.label:
        return np.inf
    eps = cfg["extent_eps"]
    cost = np.abs(np.log(a.extents + eps) - np.log(b.extents + eps)).sum()
    if np.isfinite(a.height_center) and np.isfinite(b.height_center):
        cost += cfg["height_weight"] * abs(a.height_center - b.height_center) / cfg["height_scale"]
    if cfg["require_same_class"] is False and a.label != b.label:
        cost += cfg["class_mismatch_cost"]
    return float(cost)


def candidate_matches(map_graph, new_graph, cfg):
    """Pair each map object with its k most similar new objects (and vice versa); duplicates get several."""
    map_ids, new_ids = map_graph.object_ids(), new_graph.object_ids()
    if not map_ids or not new_ids:
        return []
    C = np.array([[descriptor_cost(map_graph.objects[a], new_graph.objects[b], cfg) for b in new_ids]
                  for a in map_ids])
    C[C > cfg["max_cost"]] = np.inf
    k = cfg["k"]
    keep = set()
    for r in range(len(map_ids)):
        for c in np.argsort(C[r])[:k]:
            if np.isfinite(C[r, c]):
                keep.add((r, c))
    for c in range(len(new_ids)):
        for r in np.argsort(C[:, c])[:k]:
            if np.isfinite(C[r, c]):
                keep.add((r, c))
    return sorted((Candidate(map_ids[r], new_ids[c], float(C[r, c])) for r, c in keep),
                  key=lambda m: (m.cost, m.map_id, m.new_id))
