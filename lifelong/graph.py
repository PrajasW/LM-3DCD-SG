"""Object-level 3D scene graph built from instance-segmented point clouds."""
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import ConvexHull

STRUCTURE_CLASSES = {"floor", "wall", "ceiling"}


def is_structure(label):
    return label.lower().strip() in STRUCTURE_CLASSES


@dataclass
class ObjectNode:
    id: int
    label: str
    points: np.ndarray            # (N, 3)
    centroid: np.ndarray          # (3,)
    extents: np.ndarray           # (3,) [horizontal major, horizontal minor, vertical] (pose invariant)
    height_bottom: float          # lowest point above the floor plane (nan if no floor)
    height_center: float          # centroid height above the floor plane (nan if no floor)
    history: list = field(default_factory=list)

    @property
    def radius(self):
        return 0.5 * float(np.linalg.norm(self.extents))

    @property
    def volume(self):
        return float(np.prod(np.maximum(self.extents, 1e-3)))


@dataclass
class SceneGraph:
    scan_id: str
    objects: dict                 # id -> ObjectNode (non-structural)
    structure: dict               # id -> ObjectNode (floor / walls / ceiling)
    floor_normal: np.ndarray      # (3,) unit, pointing up; None if no floor
    floor_offset: float           # plane: n.x + d = 0
    edges: list                   # (id_a, id_b, relation)

    def object_ids(self):
        return sorted(self.objects)

    def centroids(self, ids):
        return np.stack([self.objects[i].centroid for i in ids])

    def structure_points(self):
        if not self.structure:
            return np.zeros((0, 3))
        return np.concatenate([n.points for n in self.structure.values()])

    def height_above_floor(self, pts):
        if self.floor_normal is None:
            return np.full(len(pts), np.nan)
        return pts @ self.floor_normal + self.floor_offset


def fit_floor_plane(floor_pts, all_pts):
    """Plane through floor points, normal oriented towards the bulk of the scene."""
    c = floor_pts.mean(0)
    _, _, Vt = np.linalg.svd(floor_pts - c, full_matrices=False)
    n = Vt[2]
    if np.median((all_pts - c) @ n) < 0:
        n = -n
    return n, -float(n @ c)


def _robust_extent(x, lo=2, hi=98):
    a, b = np.percentile(x, [lo, hi])
    return b - a


def _min_area_rect_axes(xy):
    """Unit axes (2, 2) of the minimum-area bounding rectangle of 2D points (rotating calipers on the hull)."""
    try:
        hull = xy[ConvexHull(xy).vertices]
    except Exception:  # degenerate (collinear) footprint
        hull = xy
    edges = np.diff(np.vstack([hull, hull[:1]]), axis=0)
    angles = np.unique(np.mod(np.arctan2(edges[:, 1], edges[:, 0]), np.pi / 2))
    best, best_area = np.eye(2), np.inf
    for a in angles:
        R = np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])
        p = hull @ R.T
        area = np.prod(p.max(0) - p.min(0))
        if area < best_area:
            best, best_area = R, area
    return best


def object_extents(pts, up):
    """Horizontal major/minor extents in the floor plane plus vertical extent; 3D PCA when no floor.

    The horizontal axes come from the minimum-area bounding rectangle, which (unlike PCA) is stable for
    objects with square footprints, so the descriptor does not change with the robot's pose.
    """
    c = pts - pts.mean(0)
    if up is None:
        _, _, Vt = np.linalg.svd(c, full_matrices=False)
        e = np.array([_robust_extent(c @ v) for v in Vt])
        return np.sort(e)[::-1]
    vertical = _robust_extent(c @ up)
    # orthonormal basis (e1, e2) of the floor plane
    e1 = np.cross(up, [1.0, 0, 0] if abs(up[0]) < 0.9 else [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    xy = np.stack([c @ e1, c @ e2], 1)
    axes = _min_area_rect_axes(xy)
    h = sorted([_robust_extent(xy @ axes[0]), _robust_extent(xy @ axes[1])], reverse=True)
    return np.array([h[0], h[1], vertical])


def build_graph(scan, min_points=50, near_dist=0.3):
    """Scene graph from the annotated instance segments of a scan (points already in the desired frame)."""
    ids = np.unique(scan.object_ids)
    ids = ids[ids != 0]
    segments = {int(i): scan.points[scan.object_ids == i] for i in ids}

    floor_ids = [i for i in segments if scan.labels.get(i, "").lower() == "floor"]
    up, d = None, 0.0
    if floor_ids:
        floor_pts = np.concatenate([segments[i] for i in floor_ids])
        if len(floor_pts) >= 3:
            up, d = fit_floor_plane(floor_pts, scan.points)

    objects, structure = {}, {}
    for i, pts in segments.items():
        if len(pts) < min_points:
            continue
        label = scan.labels.get(i, "unknown")
        centroid = pts.mean(0)
        if up is not None:
            heights = pts @ up + d
            hb, hc = float(np.percentile(heights, 2)), float(centroid @ up + d)
        else:
            hb = hc = float("nan")
        node = ObjectNode(i, label, pts, centroid, object_extents(pts, up), hb, hc)
        (structure if is_structure(label) else objects)[i] = node

    edges = [(a, b, rel) for a, b, rel in scan.relationships if a in objects and b in objects]
    related = {(a, b) for a, b, _ in edges} | {(b, a) for a, b, _ in edges}
    obj_ids = sorted(objects)
    for x, a in enumerate(obj_ids):
        for b in obj_ids[x + 1:]:
            if (a, b) in related:
                continue
            gap = np.linalg.norm(objects[a].centroid - objects[b].centroid) - objects[a].radius - objects[b].radius
            if gap < near_dist:
                edges.append((a, b, "near"))
    return SceneGraph(scan.scan_id, objects, structure, up, d, edges)
