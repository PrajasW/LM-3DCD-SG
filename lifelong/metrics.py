"""Relocalization metrics shared by every method."""
import numpy as np

from .transforms import apply, rotation_error_deg, translation_error

# RIO / 3RScan alignment thresholds (Wald et al., ICCV 2019): (translation m, rotation deg).
RIO_THRESHOLDS = [(0.10, 10.0), (0.20, 20.0)]
RR_RMSE = 0.2  # registration recall threshold used by SGAligner / SG-PGM / SG-Reg


def pose_errors(T_est, T_gt, pts=None):
    """RRE (deg), RTE (m) and, given points in the source frame, RMSE of their mapped positions (m)."""
    out = {
        "rre": rotation_error_deg(T_est[:3, :3], T_gt[:3, :3]),
        "rte": translation_error(T_est[:3, 3], T_gt[:3, 3]),
    }
    if pts is not None:
        out["rmse"] = float(np.sqrt(np.mean(np.sum((apply(T_est, pts) - apply(T_gt, pts)) ** 2, axis=1))))
    return out


def is_success(err, t_thr, r_thr):
    return err["rte"] <= t_thr and err["rre"] <= r_thr


def static_set_scores(static_pairs, gt_static_ids):
    """Precision/recall of the predicted static correspondences against unchanged instances (shared ids)."""
    correct = sum(1 for i, j in static_pairs if i == j and i in gt_static_ids)
    p = correct / len(static_pairs) if static_pairs else 0.0
    r = correct / len(gt_static_ids) if gt_static_ids else 0.0
    return p, r
