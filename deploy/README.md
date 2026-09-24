# Releases and staging

Three tiers, all on boulder:

| Tier    | Port | Code                       | Data                          | Command                 |
|---------|------|----------------------------|-------------------------------|-------------------------|
| dev     | 5003 | working tree, hot reload   | `.devdata/` test db           | `inv start --port 5003` |
| staging | 5002 | working tree, in docker    | copy of live (`staging-data/`)| `deploy/stage.sh`       |
| live    | 5001 | tagged release image       | `data/`, the real thing       | `deploy/release.sh V`   |

Images are `lute-fork:<version>` and `lute-fork:staging`. The live version is
`LUTE_RELEASE` in `~/apps/lute/.env`; changing it and running `docker compose up -d lute`
is all a deploy is. `deploy/rollback.sh` does exactly that with the previous value.

Version scheme: `<upstream version>-fork.<n>`, e.g. `3.10.3-fork.1`. Bump `n` for fork
releases; the upstream part changes when `develop` is merged into `main`.

Every release first writes a consistent gzip of the live db to `release-backups/`.
Lute's own scheduled backups still go to `backups/`.
