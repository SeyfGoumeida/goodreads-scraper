#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") <user_id> [output_dir]

Arguments:
  user_id      Goodreads user id (e.g. 12345678-jane-doe or 12345678)
  output_dir   Optional. Defaults to \$HOME/Downloads/goodreads-data/<user_id>

Scrapes the user's full library via Goodreads' public RSS feed (no login,
no CSV needed). Writes:
  <output_dir>/library.csv      - CSV in goodreads_library_export.csv format
  <output_dir>/books/<id>.json  - one JSON per book (full metadata)

To use the package's CSV-driven mode instead, set GOODREADS_CSV=/path/to/export.csv
EOF
  exit 1
}

[[ $# -lt 1 || $# -gt 2 ]] && usage

USER_ID="$1"
OUT="${2:-$HOME/Downloads/goodreads-data/$USER_ID}"

command -v goodreads-user-scraper >/dev/null || {
  echo "error: goodreads-user-scraper not on PATH" >&2; exit 3;
}

mkdir -p "$OUT"

ARGS=(
  --user_id="$USER_ID"
  --skip_user_info=True
  --output_csv="$OUT/library.csv"
  --output_dir="$OUT"
)
if [[ -n "${GOODREADS_CSV:-}" ]]; then
  [[ -f "$GOODREADS_CSV" ]] || { echo "error: GOODREADS_CSV not found: $GOODREADS_CSV" >&2; exit 2; }
  ARGS+=(--csv_path="$GOODREADS_CSV")
fi

goodreads-user-scraper "${ARGS[@]}"

echo
echo "✅ Done. Output:"
echo "   CSV:   $OUT/library.csv"
echo "   JSONs: $OUT/books/"
