"""Download a few 3RScan validation rooms (reference + rescans) from the Hugging Face mirror.

Only the files needed for Phase 1 are fetched: annotated instance PLY, semseg labels and segment json.
Pass --with-mesh / --with-sequence to also fetch meshes / RGB-D sequences (needed by some baselines and Phase 2).
"""
import argparse
import os
import sys

from huggingface_hub import hf_hub_download

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lifelong.data import Meta3RScan  # noqa: E402

REPO = "maartenImjalli143/3RScan"
FILES = ["labels.instances.annotated.v2.ply", "semseg.v2.json", "mesh.refined.0.010000.segs.v2.json"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default="data/meta")
    ap.add_argument("--out", default="data/3RScan")
    ap.add_argument("--rooms", type=int, default=4, help="number of validation rooms")
    ap.add_argument("--min-rescans", type=int, default=2)
    ap.add_argument("--ref", nargs="*", help="explicit reference scan ids (overrides --rooms)")
    ap.add_argument("--with-mesh", action="store_true")
    ap.add_argument("--with-sequence", action="store_true")
    args = ap.parse_args()

    meta = Meta3RScan(args.meta)
    if args.ref:
        refs = args.ref
    else:
        refs = sorted(r for r, e in meta.references.items()
                      if e["type"] == "validation" and len(e["scans"]) >= args.min_rescans)[: args.rooms]

    files = list(FILES)
    if args.with_mesh:
        files += ["mesh.refined.v2.obj", "mesh.refined.mtl", "mesh.refined_0.png"]
    if args.with_sequence:
        files += ["sequence.zip"]

    for ref in refs:
        scans = [ref] + meta.rescans_of(ref)
        print(f"room {ref}: {len(scans) - 1} rescans")
        for sid in scans:
            for fn in files:
                if os.path.exists(os.path.join(args.out, sid, fn)):
                    continue
                hf_hub_download(REPO, f"{sid}/{fn}", repo_type="dataset", local_dir=args.out)
    print("done:", len(refs), "rooms ->", args.out)


if __name__ == "__main__":
    main()
