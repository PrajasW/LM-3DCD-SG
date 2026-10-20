"""Rigid-transform helpers. All transforms are 4x4 homogeneous matrices acting on column vectors."""
import numpy as np
from scipy.spatial.transform import Rotation


def make_T(R, t):
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def apply(T, pts):
    return pts @ T[:3, :3].T + T[:3, 3]


def inv(T):
    R, t = T[:3, :3], T[:3, 3]
    return make_T(R.T, -R.T @ t)


def random_se3(rng, max_translation=2.0):
    """Uniform rotation on SO(3) and translation uniform in [-max_translation, max_translation]^3."""
    R = Rotation.random(random_state=rng).as_matrix()
    t = rng.uniform(-max_translation, max_translation, size=3)
    return make_T(R, t)


def rotation_error_deg(R_est, R_gt):
    cos = (np.trace(R_est.T @ R_gt) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def translation_error(t_est, t_gt):
    return float(np.linalg.norm(t_est - t_gt))


def kabsch(src, dst, weights=None, dir_src=None, dir_dst=None, dir_weight=1.0):
    """Least-squares rigid transform T with dst ~ T(src) (Umeyama without scale).

    Optional matched unit directions (e.g. the floor normals of both frames) add rotation-only terms, so two
    points plus a shared up direction already determine the rotation.
    """
    src = np.asarray(src, dtype=float)
    dst = np.asarray(dst, dtype=float)
    w = np.ones(len(src)) if weights is None else np.asarray(weights, dtype=float)
    w = w / w.sum()
    mu_s = (w[:, None] * src).sum(0)
    mu_d = (w[:, None] * dst).sum(0)
    H = ((src - mu_s) * w[:, None]).T @ (dst - mu_d)
    if dir_src is not None:
        scale = (w * np.sum((src - mu_s) ** 2, axis=1)).sum()  # comparable magnitude to the point terms
        H = H + dir_weight * scale * np.outer(dir_src, dir_dst)
    U, _, Vt = np.linalg.svd(H)
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return make_T(R, mu_d - R @ mu_s)
