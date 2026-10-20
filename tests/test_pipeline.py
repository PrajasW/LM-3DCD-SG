import os
import sys

import numpy as np
import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lifelong.candidates import candidate_matches  # noqa: E402
from lifelong.consistency import compatibility_matrix, consistent_groups  # noqa: E402
from lifelong.data import Scan  # noqa: E402
from lifelong.graph import build_graph  # noqa: E402
from lifelong.metrics import pose_errors, static_set_scores  # noqa: E402
from lifelong.relocalize import relocalize  # noqa: E402
from lifelong.transforms import apply, inv, kabsch, make_T, random_se3  # noqa: E402

CFG = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "configs", "default.yaml")))


def box_surface(rng, center, size, n=600):
    """Points on the surface of an axis-aligned box resting at center (z = bottom)."""
    pts = rng.uniform(-0.5, 0.5, size=(n, 3))
    face = rng.integers(0, 3, size=n)
    pts[np.arange(n), face] = np.sign(pts[np.arange(n), face]) * 0.5
    return pts * size + np.asarray(center) + np.array([0, 0, size[2] / 2])


def synthetic_room(rng, objects):
    """objects: list of (id, label, center_xyz, size_xyz). Adds a floor (id 1) and two walls (ids 2, 3)."""
    pts, ids, labels = [], [], {1: "floor", 2: "wall", 3: "wall"}
    floor = np.c_[rng.uniform(0, 6, (4000, 2)), np.zeros(4000)]
    wall_a = np.c_[rng.uniform(0, 6, 2000), np.zeros(2000), rng.uniform(0, 2.5, 2000)]
    wall_b = np.c_[np.zeros(2000), rng.uniform(0, 6, 2000), rng.uniform(0, 2.5, 2000)]
    for i, p in ((1, floor), (2, wall_a), (3, wall_b)):
        pts.append(p)
        ids.append(np.full(len(p), i))
    for oid, label, c, s in objects:
        p = box_surface(rng, c, np.asarray(s))
        pts.append(p)
        ids.append(np.full(len(p), oid))
        labels[oid] = label
    pts = np.concatenate(pts)
    return pts, np.concatenate(ids), labels


ROOM = [
    (10, "chair", (1.0, 1.0, 0), (0.5, 0.5, 0.9)),
    (11, "chair", (1.0, 2.0, 0), (0.5, 0.5, 0.9)),     # identical duplicate
    (12, "chair", (2.0, 1.0, 0), (0.5, 0.5, 0.9)),     # identical duplicate
    (13, "table", (1.5, 1.5, 0), (1.2, 0.8, 0.75)),
    (14, "bed", (4.0, 4.0, 0), (2.0, 1.6, 0.5)),
    (15, "cabinet", (5.5, 0.5, 0), (0.6, 0.4, 1.8)),
    (16, "box", (3.0, 5.0, 0), (0.4, 0.3, 0.3)),
    (17, "box", (3.4, 5.0, 0), (0.4, 0.3, 0.3)),
    (18, "lamp", (5.5, 5.5, 0), (0.3, 0.3, 1.5)),
    (19, "plant", (0.4, 5.5, 0), (0.4, 0.4, 0.7)),
]


def make_visits(seed=0, move_group=True):
    rng = np.random.default_rng(seed)
    pts, ids, labels = synthetic_room(rng, ROOM)
    ref = Scan("ref", pts, np.zeros_like(pts, dtype=np.uint8), ids, labels)

    room2 = []
    for oid, label, c, s in ROOM:
        c = np.array(c, float)
        if move_group and oid in (16, 17):        # two boxes carried together
            c = c + np.array([-2.0, -1.0, 0])
        room2.append((oid, label, c, s))
    pts2, ids2, labels2 = synthetic_room(rng, room2)
    T_rand = random_se3(rng, 2.0)
    new = Scan("new", apply(T_rand, pts2), np.zeros_like(pts2, dtype=np.uint8), ids2, labels2)
    return ref, new, T_rand


def test_kabsch_recovers_transform():
    rng = np.random.default_rng(1)
    T = random_se3(rng, 3.0)
    src = rng.normal(size=(20, 3))
    T_est = kabsch(src, apply(T, src))
    assert np.allclose(T_est, T, atol=1e-8)


def test_inverse_and_errors():
    rng = np.random.default_rng(2)
    T = random_se3(rng)
    assert np.allclose(T @ inv(T), np.eye(4), atol=1e-10)
    R90 = make_T(np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]]), [0.3, 0, 0.4])
    err = pose_errors(R90, np.eye(4), pts=np.zeros((1, 3)))
    assert err["rre"] == pytest.approx(90.0)
    assert err["rte"] == pytest.approx(0.5)
    assert err["rmse"] == pytest.approx(0.5)


def test_graph_is_pose_invariant():
    ref, new, _ = make_visits(move_group=False)
    g1, g2 = build_graph(ref), build_graph(new)
    assert set(g1.objects) == set(g2.objects) and len(g1.structure) == 3
    for i in g1.objects:
        assert np.allclose(g1.objects[i].extents, g2.objects[i].extents, atol=0.05)
        assert g1.objects[i].height_center == pytest.approx(g2.objects[i].height_center, abs=0.05)


def test_static_set_and_moved_group():
    ref, new, _ = make_visits()
    g1, g2 = build_graph(ref), build_graph(new)
    cands = candidate_matches(g1, g2, CFG["candidates"])
    # duplicates produce several candidates
    assert sum(c.map_id == 10 for c in cands) >= 3
    A = compatibility_matrix(g1, g2, cands, CFG["consistency"])
    groups = consistent_groups(A, cands, 2)
    static = {(cands[i].map_id, cands[i].new_id) for i in groups[0]}
    assert static == {(i, i) for i in (10, 11, 12, 13, 14, 15, 18, 19)}
    moved = [{(cands[i].map_id, cands[i].new_id) for i in g} for g in groups[1:]]
    assert {(16, 16), (17, 17)} in moved


def test_relocalize_end_to_end():
    ref, new, T_rand = make_visits()
    g1, g2 = build_graph(ref), build_graph(new)
    res = relocalize(g1, g2, CFG)
    assert res.success
    err = pose_errors(res.T, inv(T_rand))
    assert err["rre"] < 1.0 and err["rte"] < 0.05
    p, r = static_set_scores(res.static_pairs, {10, 11, 12, 13, 14, 15, 18, 19})
    assert p == 1.0 and r == 1.0


def test_relocalize_reports_failure():
    rng = np.random.default_rng(3)
    pts, ids, labels = synthetic_room(rng, ROOM[:2])
    ref = Scan("a", pts, np.zeros_like(pts, dtype=np.uint8), ids, labels)
    res = relocalize(build_graph(ref), build_graph(ref), CFG)
    assert not res.success and res.reason == "too_few_static"


def test_kabsch_with_shared_direction():
    rng = np.random.default_rng(4)
    T = random_se3(rng)
    src = np.array([[0.0, 0, 0], [1.0, 0, 0], [2.0, 0, 0]])       # collinear: rotation about x unobservable
    up = np.array([0.0, 0, 1])
    T_est = kabsch(src, apply(T, src), dir_src=up, dir_dst=T[:3, :3] @ up)
    assert np.allclose(T_est, T, atol=1e-8)



def test_relocalize_rejects_collinear_static_set():
    rng = np.random.default_rng(5)
    room = [(10, "chair", (1.0, 1.0, 0), (0.5, 0.5, 0.9)),
            (11, "table", (2.5, 1.0, 0), (1.2, 0.8, 0.75)),
            (12, "cabinet", (4.5, 1.0, 0), (0.6, 0.4, 1.8))]
    pts, ids, labels = synthetic_room(rng, room)
    ref = Scan("a", pts, np.zeros_like(pts, dtype=np.uint8), ids, labels)
    new = Scan("b", apply(random_se3(rng), pts), np.zeros_like(pts, dtype=np.uint8), ids, labels)
    res = relocalize(build_graph(ref), build_graph(new), CFG)
    assert not res.success and res.reason == "degenerate"
