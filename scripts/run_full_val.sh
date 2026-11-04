#!/bin/bash
# Full validation split end to end: download -> pairs -> all methods -> evaluation, plus the RGB-D sequences for
# Phase 2 in the background. Writes only new paths (data/pairs_val_full*.json, results/full_val/,
# baselines/work/Scan3R_full*), so the 17-pair subset results stay as they are. Meant to run inside tmux:
#   tmux new -d -s fullval 'bash scripts/run_full_val.sh'
# A failing step is logged and the remaining steps still run.
set -uo pipefail
cd "$(dirname "$0")/.."
MRPROJ=${MRPROJ_PY:-$HOME/miniconda3/envs/mrproj/bin/python}
SGBASE=${SGBASE_PY:-$HOME/miniconda3/envs/sgbase/bin/python}
SEQ_DIR=${SEQ_DIR:-/scratch/$USER/3RScan_seq}
CFG=configs/full_val.yaml
PAIRS=data/pairs_val_full.json
PAIRS_AL=data/pairs_val_full_aligned.json
OUT=results/full_val
LOG=$OUT/logs
mkdir -p "$LOG" "$SEQ_DIR"

step() {  # step <name> <command...>: run, log to $LOG/<name>.log, record status and duration
  local name=$1; shift
  local t0=$SECONDS
  echo "[$(date '+%F %T')] start $name" | tee -a "$LOG/progress.txt"
  if "$@" > "$LOG/$name.log" 2>&1; then s=ok; else s="FAILED (exit $?)"; fi
  echo "[$(date '+%F %T')] $s $name ($(( (SECONDS - t0) / 60 )) min)" | tee -a "$LOG/progress.txt"
}

# RGB-D sequences (6.8 GB) in the background; not needed by Steps 1-3.
"$MRPROJ" scripts/download_sequences.py --out "$SEQ_DIR" > "$LOG/download_sequences.log" 2>&1 &
SEQ_PID=$!
ln -sfn "$SEQ_DIR" data/3RScan_seq

step download_labels  "$MRPROJ" scripts/download_subset.py --rooms 47 --min-rescans 1
step pairs            "$MRPROJ" scripts/make_pairs.py --config $CFG
step pairs_aligned    "$MRPROJ" scripts/make_pairs.py --config $CFG --aligned

# Ours first, with an interim table, so our numbers are available before the baselines finish.
step ours             "$MRPROJ" scripts/run_ours.py --config $CFG --out-dir $OUT
step eval_ours        "$MRPROJ" scripts/evaluate.py --config $CFG --results $OUT
step classical        "$MRPROJ" scripts/run_classical.py --config $CFG --out-dir $OUT
step prep_baselines   bash baselines/adapters/prepare_baselines.sh $PAIRS baselines/work/Scan3R_full
step sgaligner        "$SGBASE" baselines/adapters/run_sgaligner.py --data-root baselines/work/Scan3R_full \
                        --pairs $PAIRS --out $OUT/sgaligner.jsonl
step sgpgm            "$SGBASE" baselines/adapters/run_sgpgm.py --data-root baselines/work/Scan3R_full \
                        --pairs $PAIRS --out $OUT/sgpgm.jsonl
step eval             "$MRPROJ" scripts/evaluate.py --config $CFG --results $OUT

# Pre-aligned rescans: the learned baselines' own setting (upper bound / adapter sanity check).
step ours_aligned       "$MRPROJ" scripts/run_ours.py --config $CFG --pairs $PAIRS_AL --out-dir $OUT --tag _aligned
step classical_aligned  "$MRPROJ" scripts/run_classical.py --config $CFG --pairs $PAIRS_AL --out-dir $OUT --tag _aligned
step prep_aligned       bash baselines/adapters/prepare_baselines.sh $PAIRS_AL baselines/work/Scan3R_full_aligned
step sgaligner_aligned  "$SGBASE" baselines/adapters/run_sgaligner.py --data-root baselines/work/Scan3R_full_aligned \
                          --pairs $PAIRS_AL --out $OUT/sgaligner_aligned.jsonl
step sgpgm_aligned      "$SGBASE" baselines/adapters/run_sgpgm.py --data-root baselines/work/Scan3R_full_aligned \
                          --pairs $PAIRS_AL --out $OUT/sgpgm_aligned.jsonl
step eval_aligned       "$MRPROJ" scripts/evaluate.py --config $CFG --pairs $PAIRS_AL --results $OUT --tag _aligned

echo "[$(date '+%F %T')] waiting for the sequence download" | tee -a "$LOG/progress.txt"
if wait $SEQ_PID; then s=ok; else s=FAILED; fi
echo "[$(date '+%F %T')] $s download_sequences: $(tail -1 "$LOG/download_sequences.log")" | tee -a "$LOG/progress.txt"
echo "[$(date '+%F %T')] all done" | tee -a "$LOG/progress.txt"
