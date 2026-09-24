#!/bin/sh
# Shared helpers for the fork's release scripts. Sourced, not executed.
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="${LUTE_DEPLOY_DIR:-$HOME/apps/lute}"
ENV_FILE="$DEPLOY_DIR/.env"
IMAGE=lute-fork

die() { echo "error: $*" >&2; exit 1; }

env_get() { grep -E "^$1=" "$ENV_FILE" 2>/dev/null | cut -d= -f2-; }
env_set() {
  touch "$ENV_FILE"
  if grep -qE "^$1=" "$ENV_FILE"; then sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE"; else echo "$1=$2" >> "$ENV_FILE"; fi
}

# Consistent copy of a live sqlite db (safe while Lute is writing).
backup_db() {  # backup_db <src.db> <dest.db.gz>
  python3 - "$1" "$2" <<'PY'
import sqlite3, sys, gzip, shutil, os
src, dest = sys.argv[1], sys.argv[2]
tmp = dest[:-3]
s = sqlite3.connect(f"file:{src}?mode=ro", uri=True); d = sqlite3.connect(tmp); s.backup(d); d.close(); s.close()
with open(tmp, "rb") as f, gzip.open(dest, "wb") as g: shutil.copyfileobj(f, g)
os.remove(tmp); print(f"backup: {dest} ({os.path.getsize(dest)//1024} KB)")
PY
}

# Wait until Lute answers on a port. Startup may run db migrations.
wait_healthy() {  # wait_healthy <port> [seconds]
  port=$1; secs=${2:-90}; i=0
  while [ $i -lt "$secs" ]; do
    if curl -sf --max-time 3 "http://localhost:$port/" | grep -q "Lute"; then echo "healthy on :$port"; return 0; fi
    i=$((i+1)); sleep 1
  done
  echo "NOT healthy on :$port after ${secs}s" >&2; return 1
}

build_image() {  # build_image <tag>
  docker build -f "$REPO/docker/Dockerfile" --build-arg INSTALL_EVERYTHING=true -t "$IMAGE:$1" "$REPO"
}
