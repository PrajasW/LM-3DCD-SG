"""Run SG-PGM (CVPR'24) scene-graph matching + rescored GeoTransformer registration on our two-visit pairs.

Mirrors scripts/inference_reg.py of the SG-PGM repo (same model, weights, dataset class and collate function) but
writes the estimated transform per pair so every method is scored by scripts/evaluate.py. The repo's own random
augmentation is disabled: the new visit was already moved by the pair's stored random transform during export.
Run in the `sgbase` env after prepare_baselines.sh.
"""
import argparse
import os.path as osp
import sys
import time

import numpy as np
import torch

ROOT = osp.abspath(osp.join(osp.dirname(__file__), "..", ".."))
SGP = osp.join(ROOT, "baselines", "sg-pgm")
sys.path[:0] = [SGP, ROOT]  # SG-PGM first: it has its own top-level `data` and `utils` packages

from data.datasets import Scan3RDataset  # noqa: E402
from data.stack_mode import build_dataloader_stack_mode, registration_collate_fn_stack_mode  # noqa: E402
from data.torch_utils import release_cuda, to_cuda  # noqa: E402
from sg_pgm import SGPGM_GeoTransformer  # noqa: E402
from utils.net_args import parse_args  # noqa: E402

from lifelong.protocol import ResultWriter, load_pairs  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=osp.join(ROOT, "baselines/work/Scan3R"))
    ap.add_argument("--pairs", default=osp.join(ROOT, "data/pairs_val.json"))
    ap.add_argument("--trained-model", default=osp.join(ROOT, "baselines/weights/sgpgm/sg-pgm_best_model.pth"))
    ap.add_argument("--geotr", default=osp.join(ROOT, "baselines/weights/geotransformer-3dmatch.pth.tar"))
    ap.add_argument("--out", default=osp.join(ROOT, "results/sgpgm.jsonl"))
    args = ap.parse_args()

    work = osp.join(args.data_root, "sgpgm_run")
    _, cfg = parse_args(["--config", osp.join(SGP, "data/sg_pgm.json"), "--save_folder", work, "--log_root", work])
    model = SGPGM_GeoTransformer(cfg).cuda()
    model.load_weights(args.trained_model, args.geotr)
    model.eval()

    dataset = Scan3RDataset(dataset_root=osp.join(args.data_root, "sgpgm_root"), split="val",
                            use_augmentation=False, predicted=False)
    loader = build_dataloader_stack_mode(
        dataset, registration_collate_fn_stack_mode, cfg.backbone.num_stages, cfg.backbone.init_voxel_size,
        cfg.backbone.init_radius, cfg.dataset.neighbor_limits, batch_size=1, num_workers=0, shuffle=False,
        distributed=False, reproducibility=True, point_limits=cfg.dataset.max_c_points)

    pairs = {(p["rescan"] + "_rand", p["ref"]): p for p in load_pairs(args.pairs)}
    writer = ResultWriter(args.out)
    it = iter(loader)
    for _ in range(len(dataset)):
        t0 = time.perf_counter()
        batch = next(it)  # collation (voxelisation, neighbour search) is part of the method's runtime
        pair = pairs[(batch["src_frame"], batch["ref_frame"])]
        try:
            with torch.no_grad():
                out = release_cuda(model(to_cuda(batch), early_stop=False))
            T, ok, err = np.asarray(out["estimated_transform"], dtype=float), True, ""
        except Exception as e:  # e.g. no scene-graph matches survive top-k -> no correspondences
            T, ok, err = np.eye(4), False, repr(e)[:200]
            torch.cuda.empty_cache()
        elapsed = time.perf_counter() - t0
        writer.write(pair, T, ok, elapsed, error=err)
        print(f"{batch['src_frame']} -> {batch['ref_frame']}: ok={ok} {elapsed:.2f}s {err}", flush=True)
    writer.close()


if __name__ == "__main__":
    main()
