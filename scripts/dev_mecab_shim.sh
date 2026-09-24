#!/bin/sh
# Make Japanese parsing work in a venv without a system MeCab install.
# Uses the libmecab bundled in the mecab-python3 wheel and the ipadic pip dictionary,
# and installs two shims so natto-py can find them. Run from the repo root with
# the venv activated. Safe to re-run.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${VIRTUAL_ENV:-$ROOT/.venv}"
uv pip install -q mecab-python3 ipadic
SO="$(ls "$VENV"/lib/python*/site-packages/mecab_python3.libs/libmecab*.so* | head -1)"
DIC="$("$VENV/bin/python" -c 'import ipadic; print(ipadic.DICDIR)')"
mkdir -p "$ROOT/.devdata/mecab/lib"
ln -sf "$SO" "$ROOT/.devdata/mecab/lib/libmecab.so"
printf 'dicdir = %s\n' "$DIC" > "$ROOT/.devdata/mecab/mecabrc"
cat > "$VENV/bin/mecab-config" <<SHIM
#!/bin/sh
case "\$1" in
  --libs-only-L) echo "$ROOT/.devdata/mecab/lib" ;;
  --dicdir) echo "$DIC" ;;
  --version) echo "0.996" ;;
  *) echo "unrecognized" ;;
esac
SHIM
cat > "$VENV/bin/mecab" <<SHIM
#!/bin/sh
[ "\$1" = "-D" ] && printf 'filename:\t$DIC/sys.dic\ncharset:\tutf8\n' || echo unrecognized
SHIM
chmod +x "$VENV/bin/mecab-config" "$VENV/bin/mecab"
if ! grep -q MECABRC "$VENV/bin/activate"; then
  printf '\n# Lute dev: pip-bundled MeCab, see scripts/dev_mecab_shim.sh\nexport MECABRC="%s/.devdata/mecab/mecabrc"\nexport MECAB_CHARSET=utf8\n' "$ROOT" >> "$VENV/bin/activate"
fi
echo "MeCab shim installed. Re-activate the venv, then: python -m pytest tests/unit/parse/test_JapaneseParser.py"
