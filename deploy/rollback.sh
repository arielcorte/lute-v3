#!/bin/sh
# Put a previous release back on :5001. Data is untouched (schema is
# forward-compatible across fork releases; restore a release-backups/*.db.gz
# by hand only if a migration went wrong).
#
#   deploy/rollback.sh              # back to LUTE_PREVIOUS_RELEASE
#   deploy/rollback.sh 3.10.3-fork.1
set -e
. "$(dirname "$0")/common.sh"
TARGET=${1:-$(env_get LUTE_PREVIOUS_RELEASE)}
[ -n "$TARGET" ] || die "no previous release recorded; pass a version"
docker image inspect "$IMAGE:$TARGET" >/dev/null 2>&1 || die "no image $IMAGE:$TARGET on this host"
CUR=$(env_get LUTE_RELEASE)
env_set LUTE_PREVIOUS_RELEASE "$CUR"
env_set LUTE_RELEASE "$TARGET"
cd "$DEPLOY_DIR" && docker compose up -d lute
wait_healthy 5001 && echo "== live is $TARGET (was $CUR)"
