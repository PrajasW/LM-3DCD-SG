"""Download the RGB-D sequences (sequence.zip: depth .pgm, color .jpg, camera pose per frame) of 3RScan scans.

Needed for Step 5 (removed / not observed). Fetches in parallel from the Hugging Face mirror; already downloaded files
are skipped, so the script can be re-run after an interruption.
  python scripts/download_sequences.py --split validation --out /scratch/$USER/3RScan_seq
"""
import argparse
import os
import sys

from huggingface_hub import snapshot_download

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lifelong.data import Meta3RScan  # noqa: E402

REPO = "maartenImjalli143/3RScan"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default="data/meta")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="validation")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    meta = Meta3RScan(args.meta)
    scans = []
    for ref, e in sorted(meta.references.items()):
        if e["type"] == args.split:
            scans += [ref] + meta.rescans_of(ref)
    print(f"{len(scans)} scans ({args.split}) -> {args.out}", flush=True)
    snapshot_download(REPO, repo_type="dataset", local_dir=args.out, max_workers=args.workers,
                      allow_patterns=[f"{s}/sequence.zip" for s in scans])
    have = sum(os.path.exists(os.path.join(args.out, s, "sequence.zip")) for s in scans)
    print(f"done: {have}/{len(scans)} sequence.zip present", flush=True)


if __name__ == "__main__":
    main()
