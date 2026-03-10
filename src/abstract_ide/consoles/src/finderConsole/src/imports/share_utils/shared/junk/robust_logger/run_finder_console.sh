#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/path/to/your/app"
VENV="/home/…/miniconda/envs/…"
LOG_DIR="${HOME}/.cache/abstract_finder"
RUN_LOG="${LOG_DIR}/runner.log"
mkdir -p "$LOG_DIR"

# Only one instance
exec 9> "${LOG_DIR}/.lock"
flock -n 9 || { echo "Already running"; exit 1; }

export PYTHONUNBUFFERED=1

while true; do
  echo "[$(date -Is)] starting app" | tee -a "$RUN_LOG"
  # activate env
  source "${VENV}/bin/activate"
  # stdbuf makes Python flush stdout so your QText appender sees it quickly
  if ! stdbuf -oL -eL python3 -m your_app_entrypoint 2>&1 | tee -a "${LOG_DIR}/finder_stdout.log"; then
    code=$?
    echo "[$(date -Is)] crashed with code ${code}" | tee -a "$RUN_LOG"
  else
    echo "[$(date -Is)] clean exit" | tee -a "$RUN_LOG"
    exit 0
  fi
  sleep 2  # backoff
done
