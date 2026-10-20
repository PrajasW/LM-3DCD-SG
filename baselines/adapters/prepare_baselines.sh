#!/bin/bash
# Export a pairs file into the SGAligner / SG-PGM data layout and run SGAligner's own preprocessing on it.
#   bash baselines/adapters/prepare_baselines.sh data/pairs_val.json baselines/work/Scan3R
set -euo pipefail
PAIRS=$(realpath "$1"); WORK=$(realpath -m "$2")
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
MRPROJ=${MRPROJ_PY:-$HOME/miniconda3/envs/mrproj/bin/python}
SGBASE=${SGBASE_PY:-$HOME/miniconda3/envs/sgbase/bin/python}

rm -rf "$WORK"
"$MRPROJ" "$ROOT/baselines/adapters/export_scan3r.py" --pairs "$PAIRS" --out "$WORK"

# SGAligner preprocessing (per-scan pickles + BOW node/edge features), unmodified, on full scans.
sed "s#^  root_dir:.*#  root_dir: $WORK#" "$ROOT/baselines/adapters/configs/sgaligner_scan.yaml" > "$WORK/preprocess.yaml"
(cd "$ROOT/baselines/sgaligner" && SCAN3R_ORIG_DIR="$WORK" "$SGBASE" preprocessing/scan3r/preprocess.py --config "$WORK/preprocess.yaml" --split val)

# SG-PGM reads <root>/out/{scenes,files}; its val loader also opens <root>/scenes/<scan>/labels.instances.align.annotated.v2.ply
# (only for its own Chamfer metric, which we do not use).
mkdir -p "$WORK/sgpgm_root/out" "$WORK/sgpgm_root/scenes"
ln -s "$WORK/scans" "$WORK/sgpgm_root/out/scenes"
ln -s "$WORK/files" "$WORK/sgpgm_root/out/files"
for d in "$WORK"/scans/*_rand; do
  r=$(basename "$d" _rand); mkdir -p "$WORK/sgpgm_root/scenes/$r"
  ln -s "$ROOT/data/3RScan/$r/labels.instances.annotated.v2.ply" "$WORK/sgpgm_root/scenes/$r/labels.instances.align.annotated.v2.ply"
done
echo "prepared $WORK"
