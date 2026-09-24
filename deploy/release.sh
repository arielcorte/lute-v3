#!/bin/sh
# Cut a release of the fork and put it live on :5001.
#
#   deploy/release.sh 3.10.3-fork.2
#
# Steps: assert clean main -> git tag -> build image -> back up live db ->
# switch compose to the new image -> health check -> on failure, roll back.
set -e
. "$(dirname "$0")/common.sh"
V=$1; [ -n "$V" ] || die "usage: release.sh <version>  (e.g. 3.10.3-fork.2)"

cd "$REPO"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "release from main only"
[ -z "$(git status --porcelain)" ] || die "working tree not clean"
git rev-parse -q --verify "refs/tags/$V" >/dev/null && die "tag $V already exists"

echo "== tag $V"; git tag -a "$V" -m "Release $V"
echo "== build $IMAGE:$V"; build_image "$V"

CUR=$(env_get LUTE_RELEASE)
echo "== backup live db (current release: ${CUR:-none})"
mkdir -p "$DEPLOY_DIR/release-backups"
backup_db "$DEPLOY_DIR/data/lute.db" "$DEPLOY_DIR/release-backups/pre-$V-$(date +%Y%m%d-%H%M%S).db.gz"

echo "== switch live to $V"
[ -n "$CUR" ] && env_set LUTE_PREVIOUS_RELEASE "$CUR"
env_set LUTE_RELEASE "$V"
cd "$DEPLOY_DIR" && docker compose up -d lute

if wait_healthy 5001; then
  echo "== live is $V"; git -C "$REPO" push -q origin "refs/tags/$V" && echo "tag pushed"
else
  echo "== health check failed, rolling back"; docker compose logs --tail=40 lute
  "$REPO/deploy/rollback.sh"; exit 1
fi
