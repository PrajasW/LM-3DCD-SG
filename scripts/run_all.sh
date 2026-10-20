#!/bin/bash
# Phase 1 end to end: pairs -> our method -> all baselines -> evaluation tables.
#   bash scripts/run_all.sh            (expects data/3RScan + data/meta, see README)
set -euo pipefail
cd "$(dirname "$0")/.."
MRPROJ=${MRPROJ_PY:-$HOME/miniconda3/envs/mrproj/bin/python}
SGBASE=${SGBASE_PY:-$HOME/miniconda3/envs/sgbase/bin/python}

echo "== unit tests";                 "$MRPROJ" -m pytest -q tests
echo "== pairs";                      "$MRPROJ" scripts/make_pairs.py
                                      "$MRPROJ" scripts/make_pairs.py --aligned

echo "== ours (two-visit protocol)";  "$MRPROJ" scripts/run_ours.py
echo "== FPFH+RANSAC, FPFH+TEASER++"; "$MRPROJ" scripts/run_classical.py

echo "== SGAligner / SG-PGM data";    bash baselines/adapters/prepare_baselines.sh data/pairs_val.json baselines/work/Scan3R
echo "== SGAligner";                  "$SGBASE" baselines/adapters/run_sgaligner.py
echo "== SG-PGM";                     "$SGBASE" baselines/adapters/run_sgpgm.py

# Upper bound for the learned baselines: rescans pre-aligned to the reference (their training/eval setting).
echo "== aligned-frame sanity check"
bash baselines/adapters/prepare_baselines.sh data/pairs_val_aligned.json baselines/work/Scan3R_aligned
"$MRPROJ" scripts/run_ours.py --pairs data/pairs_val_aligned.json --tag _aligned
"$MRPROJ" scripts/run_classical.py --pairs data/pairs_val_aligned.json --tag _aligned
"$SGBASE" baselines/adapters/run_sgaligner.py --data-root baselines/work/Scan3R_aligned \
    --pairs data/pairs_val_aligned.json --out results/sgaligner_aligned.jsonl
"$SGBASE" baselines/adapters/run_sgpgm.py --data-root baselines/work/Scan3R_aligned \
    --pairs data/pairs_val_aligned.json --out results/sgpgm_aligned.jsonl

echo "== evaluation"
"$MRPROJ" scripts/evaluate.py
"$MRPROJ" scripts/evaluate.py --pairs data/pairs_val_aligned.json --tag _aligned
