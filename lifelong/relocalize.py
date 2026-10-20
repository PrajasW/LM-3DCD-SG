"""Steps 1-3 end to end: relocalize a new visit's scene graph in the map's scene graph."""
import time
from dataclasses import dataclass, field

import numpy as np

from .candidates import candidate_matches
from .consistency import compatibility_matrix, consistent_groups
from .pose import centroid_pose, refine_icp


@dataclass
class RelocResult:
    success: bool                       # False when the method declines to return a pose
    T: np.ndarray                       # new-visit frame -> map frame (identity if not successful)
    T_centroid: np.ndarray              # before ICP (identity if not available)
    static_pairs: list                  # [(map_id, new_id)] in the largest consistent group
    moved_groups: list                  # further consistent groups [[(map_id, new_id), ...]] (used in Phase 2)
    n_candidates: int
    fitness: float = float("nan")
    rmse: float = float("nan")
    reason: str = ""
    timings: dict = field(default_factory=dict)


def relocalize(map_graph, new_graph, cfg, refine=True):
    t0 = time.perf_counter()
    cands = candidate_matches(map_graph, new_graph, cfg["candidates"])
    t1 = time.perf_counter()
    A = compatibility_matrix(map_graph, new_graph, cands, cfg["consistency"])
    groups = consistent_groups(A, cands, cfg["consistency"]["min_group_size"])
    t2 = time.perf_counter()
    as_pairs = lambda g: [(cands[i].map_id, cands[i].new_id) for i in g]
    static = as_pairs(groups[0]) if groups else []
    moved = [as_pairs(g) for g in groups[1:]]

    res = RelocResult(False, np.eye(4), np.eye(4), static, moved, len(cands))
    T0, reason = centroid_pose(map_graph, new_graph, static, cfg["pose"])
    if T0 is None:
        res.reason = reason
    else:
        res.T_centroid = T0
        if refine:
            T, fit, rmse = refine_icp(map_graph, new_graph, static, T0, cfg["pose"])
            res.fitness, res.rmse = fit, rmse
            if fit < cfg["pose"]["min_fitness"]:
                res.reason = "poor_alignment"
            else:
                res.success, res.T = True, T
        else:
            res.success, res.T = True, T0
    t3 = time.perf_counter()
    res.timings = {"candidates": t1 - t0, "consistency": t2 - t1, "pose": t3 - t2, "total": t3 - t0}
    return res
