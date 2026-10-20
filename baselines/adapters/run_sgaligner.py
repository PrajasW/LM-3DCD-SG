"""Run SGAligner (ICCV'23) node alignment + GeoTransformer registration on our two-visit pairs.

Mirrors src/inference/sgaligner/inference_align_reg.py (AlignerRegTester.eval_step) but returns the estimated
transform per pair instead of the repo's own metrics, so every method is scored by scripts/evaluate.py.
Run in the `sgbase` env after export_scan3r.py + SGAligner's preprocess.py.
"""
import argparse
import logging
import os.path as osp
import sys
import time

import numpy as np
import torch

ROOT = osp.abspath(osp.join(osp.dirname(__file__), "..", ".."))
SGA = osp.join(ROOT, "baselines", "sgaligner")
sys.path[:0] = [ROOT, SGA, osp.join(SGA, "src")]

from aligner.sg_aligner import MultiModalEncoder  # noqa: E402
from configs import config, update_config  # noqa: E402
from datasets.loaders import get_val_dataloader  # noqa: E402
from engine.registration_evaluator import RegistrationEvaluator  # noqa: E402
from utils import alignment, scan3r, torch_util  # noqa: E402

from lifelong.protocol import ResultWriter, load_pairs  # noqa: E402
from lifelong.transforms import make_T  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=osp.join(ROOT, "baselines/adapters/configs/sgaligner_scan.yaml"))
    ap.add_argument("--data-root", default=osp.join(ROOT, "baselines/work/Scan3R"))
    ap.add_argument("--pairs", default=osp.join(ROOT, "data/pairs_val.json"))
    ap.add_argument("--snapshot", default=osp.join(ROOT, "baselines/weights/sgaligner/sgaligner_pct_gat_rel_attr.pth.tar"))
    ap.add_argument("--reg-snapshot", default=osp.join(ROOT, "baselines/weights/geotransformer-3dmatch.pth.tar"))
    ap.add_argument("--out", default=osp.join(ROOT, "results/sgaligner.jsonl"))
    args = ap.parse_args()

    cfg = update_config(config, args.config, ensure_dir=False)
    cfg.defrost()
    cfg.data.root_dir = args.data_root
    cfg.freeze()
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    logger = logging.getLogger("sgaligner")
    logging.basicConfig(level=logging.INFO)
    device = torch.device("cuda")

    model = MultiModalEncoder(modules=cfg.modules, rel_dim=cfg.model.rel_dim, attr_dim=cfg.model.attr_dim).to(device)
    model.load_state_dict(torch.load(args.snapshot, map_location=device)["model"], strict=True)
    model.eval()
    reg = RegistrationEvaluator(device, cfg, args.reg_snapshot, logger)
    dataset, loader = get_val_dataloader(cfg)

    pairs = {(p["rescan"] + "_rand", p["ref"]): p for p in load_pairs(args.pairs)}
    writer = ResultWriter(args.out)
    for data_dict in loader:
        t0 = time.perf_counter()
        src_id, ref_id = data_dict["scene_ids"][0]
        with torch.no_grad():
            out = model(torch_util.to_cuda(data_dict))
        data_dict = torch_util.release_cuda(data_dict)
        emb = out["joint"] if len(cfg.modules) > 1 else out[cfg.modules[0]]
        emb = emb / emb.norm(dim=1)[:, None]
        rank_list = torch.argsort(1 - emb @ emb.T, dim=1)
        src_count = data_dict["graph_per_obj_count"][0][0]
        node_corrs = alignment.compute_node_corrs(rank_list, src_count, cfg.reg_model.K)
        node_corrs = alignment.get_node_corrs_objects_ids(node_corrs, data_dict["obj_ids"], 0)

        c = data_dict["pcl_center"][0]
        src_points, src_ply = scan3r.load_plydata_npy(osp.join(dataset.scans_scenes_dir, src_id, "data.npy"), return_ply_data=True)
        ref_points, ref_ply = scan3r.load_plydata_npy(osp.join(dataset.scans_scenes_dir, ref_id, "data.npy"), return_ply_data=True)
        reg_data = {"node_corrs": node_corrs, "src_points": src_points - c, "ref_points": ref_points - c,
                    "src_plydata": src_ply, "ref_plydata": ref_ply, "gt_transform": np.eye(4)}
        T_c = reg.run_aligner_registration(reg_data, evaluate_registration=False)
        elapsed = time.perf_counter() - t0

        pair = pairs[(src_id, ref_id)]
        if T_c is None:
            writer.write(pair, np.eye(4), False, elapsed, n_node_corrs=len(node_corrs))
        else:
            # The repo registers centred clouds; undo the centring: T = Tr(c) T_c Tr(-c).
            T = make_T(np.eye(3), c) @ np.asarray(T_c, dtype=float) @ make_T(np.eye(3), -c)
            writer.write(pair, T, True, elapsed, n_node_corrs=len(node_corrs))
        logger.info(f"{src_id} -> {ref_id}: {len(node_corrs)} node corrs, {elapsed:.2f}s")
    writer.close()


if __name__ == "__main__":
    main()
