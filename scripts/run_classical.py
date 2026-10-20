"""Training-free point-level baselines on the same two-visit pairs.

  fpfh_ransac : Open3D FPFH + RANSAC (mutual filter) + point-to-plane ICP
  fpfh_teaser : FPFH mutual nearest neighbours + TEASER++ (max-clique, GNC-TLS) + point-to-plane ICP

Both see the whole reference scan and the whole (randomly transformed) rescan, like our method.
"""
import argparse
import os
import sys
import time

import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lifelong.config import load_config  # noqa: E402
from lifelong.protocol import ResultWriter, load_pair_scans, load_pairs  # noqa: E402

reg = o3d.pipelines.registration


def preprocess(points, voxel):
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points)).voxel_down_sample(voxel)
    pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=2 * voxel, max_nn=30))
    # FPFH depends on the normal sign; Open3D's default sign is frame dependent, so orient normals towards the
    # scan centre (into the room), which is unaffected by the random rigid transform.
    pcd.orient_normals_towards_camera_location(pcd.get_center())
    fpfh = reg.compute_fpfh_feature(pcd, o3d.geometry.KDTreeSearchParamHybrid(radius=5 * voxel, max_nn=100))
    return pcd, fpfh


def icp(src, dst, T, voxel):
    for dist in (4 * voxel, 2 * voxel, voxel):
        T = reg.registration_icp(src, dst, dist, T, reg.TransformationEstimationPointToPlane(),
                                 reg.ICPConvergenceCriteria(max_iteration=50)).transformation
    return np.asarray(T)


def fpfh_ransac(src, dst, fs, fd, voxel):
    dist = 1.5 * voxel
    res = reg.registration_ransac_based_on_feature_matching(
        src, dst, fs, fd, True, dist, reg.TransformationEstimationPointToPoint(False), 3,
        [reg.CorrespondenceCheckerBasedOnEdgeLength(0.9), reg.CorrespondenceCheckerBasedOnDistance(dist)],
        reg.RANSACConvergenceCriteria(1_000_000, 0.999))
    return np.asarray(res.transformation)


def mutual_nn(fs, fd):
    a, b = np.asarray(fs.data).T, np.asarray(fd.data).T
    _, ab = cKDTree(b).query(a, k=1, workers=-1)
    _, ba = cKDTree(a).query(b, k=1, workers=-1)
    idx = np.arange(len(a))
    keep = ba[ab] == idx
    return idx[keep], ab[keep]


def fpfh_teaser(src, dst, fs, fd, voxel, max_corr=10000):
    import teaserpp_python

    i, j = mutual_nn(fs, fd)
    if len(i) > max_corr:
        sel = np.random.default_rng(0).choice(len(i), max_corr, replace=False)
        i, j = i[sel], j[sel]
    params = teaserpp_python.RobustRegistrationSolver.Params()
    params.cbar2 = 1.0
    params.noise_bound = voxel
    params.estimate_scaling = False
    params.rotation_estimation_algorithm = teaserpp_python.RobustRegistrationSolver.ROTATION_ESTIMATION_ALGORITHM.GNC_TLS
    params.rotation_gnc_factor = 1.4
    params.rotation_max_iterations = 100
    params.rotation_cost_threshold = 1e-12
    solver = teaserpp_python.RobustRegistrationSolver(params)
    solver.solve(np.asarray(src.points)[i].T, np.asarray(dst.points)[j].T)
    sol = solver.getSolution()
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = sol.rotation, sol.translation
    return T


METHODS = {"fpfh_ransac": fpfh_ransac, "fpfh_teaser": fpfh_teaser}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--pairs", default=None)
    ap.add_argument("--methods", nargs="+", default=list(METHODS))
    ap.add_argument("--voxel", type=float, default=0.05)
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    cfg = load_config(args.config)
    pairs = load_pairs(args.pairs or cfg["data"]["pairs"])
    o3d.utility.random.seed(0)

    writers = {m: ResultWriter(os.path.join(args.out_dir, f"{m}{args.tag}.jsonl")) for m in args.methods}
    for pair in tqdm(pairs, desc="classical"):
        ref, new = load_pair_scans(pair, cfg["data"]["root"])
        for m in args.methods:
            t = time.perf_counter()
            src, fs = preprocess(new.points, args.voxel)
            dst, fd = preprocess(ref.points, args.voxel)
            T = METHODS[m](src, dst, fs, fd, args.voxel)
            T = icp(src, dst, T, args.voxel)
            writers[m].write(pair, T, True, time.perf_counter() - t)
    for w in writers.values():
        w.close()


if __name__ == "__main__":
    main()
