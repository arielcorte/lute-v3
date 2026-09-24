#!/bin/sh
# Run whatever is in the working tree (any branch, dirty is fine) on :5002
# against a COPY of the live data. Break it freely.
#
#   deploy/stage.sh               # rebuild + restart staging
#   deploy/stage.sh --fresh-data  # also re-clone live data into staging-data/
#   deploy/stage.sh --down        # stop staging
set -e
. "$(dirname "$0")/common.sh"
cd "$DEPLOY_DIR"
case "$1" in
  --down) docker compose --profile staging down lute-staging; exit 0 ;;
  --fresh-data)
    echo "== cloning live data -> staging-data"
    mkdir -p staging-data staging-backups
    rsync -a --delete --exclude lute.db data/ staging-data/
    python3 -c "
import sqlite3; s=sqlite3.connect('file:data/lute.db?mode=ro', uri=True); d=sqlite3.connect('staging-data/lute.db'); s.backup(d); d.close()"
    ;;
esac
echo "== build $IMAGE:staging from $(git -C "$REPO" rev-parse --abbrev-ref HEAD) @ $(git -C "$REPO" rev-parse --short HEAD)"
build_image staging
docker compose --profile staging up -d lute-staging
wait_healthy 5002 && echo "== staging: http://localhost:5002"
