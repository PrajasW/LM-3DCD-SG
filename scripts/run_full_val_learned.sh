#!/bin/bash
# Re-run only the learned baselines (SGAligner, SG-PGM) on the full validation split, after run_full_val.sh has
# prepared their inputs (baselines/work/Scan3R_full*). Waits until CUDA works in the sgbase env (re-tested every
# WAIT_STEP seconds, up to WAIT_MAX), then runs the four baseline steps and re-evaluates. Meant to run inside tmux:
#   tmux new -d -s learned 'bash scripts/run_full_val_learned.sh'
# or on a fresh GPU job:  srun --gres=gpu:1 bash scripts/run_full_val_learned.sh
set -uo pipefail
cd "$(dirname "$0")/.."
MRPROJ=${MRPROJ_PY:-$HOME/miniconda3/envs/mrproj/bin/python}
SGBASE=${SGBASE_PY:-$HOME/miniconda3/envs/sgbase/bin/python}
WAIT_STEP=${WAIT_STEP:-600}
WAIT_MAX=${WAIT_MAX:-172800}
CFG=configs/full_val.yaml
PAIRS=data/pairs_val_full.json
PAIRS_AL=data/pairs_val_full_aligned.json
OUT=results/full_val
LOG=$OUT/logs
PROG=$LOG/progress_learned.txt
mkdir -p "$LOG"

step() {  # step <name> <command...>: run, log to $LOG/<name>.log, record status and duration
  local name=$1; shift
  local t0=$SECONDS
  echo "[$(date '+%F %T')] start $name" | tee -a "$PROG"
  if "$@" > "$LOG/$name.log" 2>&1; then s=ok; else s="FAILED (exit $?)"; fi
  echo "[$(date '+%F %T')] $s $name ($(( (SECONDS - t0) / 60 )) min)" | tee -a "$PROG"
}

waited=0
until "$SGBASE" -c "import torch; torch.zeros(1).cuda()" > /dev/null 2>&1; do
  if (( waited >= WAIT_MAX )); then
    echo "[$(date '+%F %T')] gave up: CUDA still unavailable after $(( waited / 3600 )) h" | tee -a "$PROG"
    exit 1
  fi
  echo "[$(date '+%F %T')] CUDA unavailable on $(hostname), retrying in $(( WAIT_STEP / 60 )) min" | tee -a "$PROG"
  sleep "$WAIT_STEP"; waited=$(( waited + WAIT_STEP ))
done
echo "[$(date '+%F %T')] CUDA available on $(hostname)" | tee -a "$PROG"

step sgaligner          "$SGBASE" baselines/adapters/run_sgaligner.py --data-root baselines/work/Scan3R_full \
                          --pairs $PAIRS --out $OUT/sgaligner.jsonl
step sgpgm              "$SGBASE" baselines/adapters/run_sgpgm.py --data-root baselines/work/Scan3R_full \
                          --pairs $PAIRS --out $OUT/sgpgm.jsonl
step eval               "$MRPROJ" scripts/evaluate.py --config $CFG --results $OUT
step sgaligner_aligned  "$SGBASE" baselines/adapters/run_sgaligner.py --data-root baselines/work/Scan3R_full_aligned \
                          --pairs $PAIRS_AL --out $OUT/sgaligner_aligned.jsonl
step sgpgm_aligned      "$SGBASE" baselines/adapters/run_sgpgm.py --data-root baselines/work/Scan3R_full_aligned \
                          --pairs $PAIRS_AL --out $OUT/sgpgm_aligned.jsonl
step eval_aligned       "$MRPROJ" scripts/evaluate.py --config $CFG --pairs $PAIRS_AL --results $OUT --tag _aligned
echo "[$(date '+%F %T')] all done" | tee -a "$PROG"
