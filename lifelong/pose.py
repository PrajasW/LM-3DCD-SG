"""Step 3: robot pose from the static objects, refined by ICP on their points plus floor and walls."""
import numpy as np
import open3d as o3d

from .transforms import kabsch


def _pcd(pts, voxel):
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts))
    pcd = pcd.voxel_down_sample(voxel)
    pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=4 * voxel, max_nn=30))
    return pcd


def centroid_pose(map_graph, new_graph, pairs, cfg):
    """Rigid transform new->map from matched centroids (plus the floor normals when both visits have a floor).

    Returns (None, reason) when the static set is too weak evidence for a pose: fewer than `min_static` matches,
    or centroids that are (nearly) collinear. The floor normal would make collinear sets solvable, but on the dev
    rooms such sets were mostly groups of objects that moved together, so they are still rejected; the normal
    only conditions the rotation estimate.
    """
    if len(pairs) < max(3, cfg["min_static"]):
        return None, "too_few_static"
    src = new_graph.centroids([j for _, j in pairs])
    dst = map_graph.centroids([i for i, _ in pairs])
    w = np.array([1.0 / (0.1 + max(map_graph.objects[i].radius, new_graph.objects[j].radius)) for i, j in pairs])
    if np.linalg.svd(src - src.mean(0), compute_uv=False)[1] / np.sqrt(len(src)) < cfg["min_spread"]:
        return None, "degenerate"
    if cfg["use_floor_normal"] and map_graph.floor_normal is not None and new_graph.floor_normal is not None:
        return kabsch(src, dst, w, new_graph.floor_normal, map_graph.floor_normal), None
    return kabsch(src, dst, w), None


def refine_icp(map_graph, new_graph, pairs, T0, cfg):
    """Point-to-plane ICP on static objects and structure; returns (T, fitness, inlier_rmse)."""
    voxel = cfg["icp_voxel"]
    src = np.concatenate([new_graph.objects[j].points for _, j in pairs] + [new_graph.structure_points()])
    dst = np.concatenate([map_graph.objects[i].points for i, _ in pairs] + [map_graph.structure_points()])
    src_pcd, dst_pcd = _pcd(src, voxel), _pcd(dst, voxel)
    T = T0
    for dist in cfg["icp_distances"]:
        T = o3d.pipelines.registration.registration_icp(
            src_pcd, dst_pcd, dist, T,
            o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=cfg["icp_iterations"]),
        ).transformation
    ev = o3d.pipelines.registration.evaluate_registration(src_pcd, dst_pcd, cfg["icp_distances"][-1], T)
    return np.asarray(T), float(ev.fitness), float(ev.inlier_rmse)
