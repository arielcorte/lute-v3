# This fork

Opinionated fork of [LuteOrg/lute-v3](https://github.com/LuteOrg/lute-v3): a new UI and
AI-assisted lookups, on top of the upstream engine. Fixes flow both ways.

## Branches

| Branch    | Tracks             | Purpose                                                   |
|-----------|--------------------|-----------------------------------------------------------|
| `develop` | `upstream/develop` | Pristine upstream. Never commit here. Base for fix PRs.   |
| `main`    | `origin/main`      | The fork: UI + AI work. Merges `develop` in regularly.    |
| `fix/*`   | off `develop`      | One upstreamable fix each. PR'd to LuteOrg, merged to main.|
| `feat/*`  | off `main`         | Fork-only features.                                       |

## Upstream fixes -> fork

```sh
git fetch upstream
git checkout develop && git merge --ff-only upstream/develop
git checkout main && git merge develop
```

## Fork fixes -> upstream

Found a bug while working on `main`? Fix it on a branch off `develop`, not off `main`:

```sh
git checkout -b fix/short-name develop
# ...fix, add a test...
inv black && inv lint && inv full      # upstream CI runs all three
git push -u origin fix/short-name
gh pr create --repo LuteOrg/lute-v3 --base develop
git checkout main && git merge fix/short-name   # don't wait for upstream to use it
```

Upstream rules (from the [Contributing wiki](https://github.com/LuteOrg/lute-v3/wiki/Contributing)):
one thing per PR, no new dependencies unless unavoidable, tests required,
target `develop`, and discuss anything not covered by an existing issue on
Discord or GitHub first. The maintainer merges slowly; that's normal.

Keeping conflicts down: put fork-only code in new modules (e.g. `lute/ai/`, a
separate frontend package) rather than editing upstream files where avoidable.
Template and JS edits will conflict on merge; accept that for the UI work.

## Upstream issues worth tracking

- AI lookups: [#17](https://github.com/LuteOrg/lute-v3/issues/17),
  [#519](https://github.com/LuteOrg/lute-v3/issues/519). Maintainer's acceptable design:
  Python back-end route, provider class per AI service, per-language user-editable
  prompts, API keys in settings.
- JSON API for a new frontend: [#297](https://github.com/LuteOrg/lute-v3/issues/297).
- Dictionaries: offline files [#228](https://github.com/LuteOrg/lute-v3/issues/228),
  nicknames [#330](https://github.com/LuteOrg/lute-v3/issues/330).

## Dev environment (no root needed)

```sh
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
git submodule update --init                 # language definitions (lute/db/language_defs)
cp lute/config/config.yml.example lute/config/config.yml
# then set: ENV: dev, DBNAME: test_lute.db, DATAPATH: <abs path>/.devdata
scripts/dev_mecab_shim.sh                    # Japanese parser support, no root
python -m pytest tests/unit -q               # ~90s
inv start                                    # http://localhost:5001
```

Japanese parsing needs MeCab. Instead of `apt install mecab`, this checkout uses the
pip-bundled library: `mecab-python3` ships `libmecab.so`, `ipadic` ships the dictionary,
and two tiny shims (`.venv/bin/mecab-config`, `.venv/bin/mecab`) tell natto-py where
they are. `.venv/bin/activate` exports `MECABRC` and `MECAB_CHARSET`. If you rebuild the
venv, run `scripts/dev_mecab_shim.sh` again.

`.devdata/` and `.venv/` are excluded via `.git/info/exclude`, so they never show up
in upstream PRs.
