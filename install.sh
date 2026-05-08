#!/usr/bin/env bash
set -euo pipefail

# Installs goodreads-user-scraper from PyPI and applies local patches that:
#  - replace broken HTML shelf scraping with public RSS feed paginating
#  - add --csv_path  (drive shelves from a Goodreads CSV export)
#  - add --output_csv (single CSV in goodreads_library_export.csv format)

HERE="$(cd "$(dirname "$0")" && pwd)"

echo "→ Installing goodreads-user-scraper from PyPI..."
pip install --quiet --upgrade goodreads-user-scraper

PKG_DIR="$(python3 -c 'import scraper, os; print(os.path.dirname(scraper.__file__))')"
echo "→ Package location: $PKG_DIR"

echo "→ Applying patches..."
cp "$HERE/patches/__main__.py"     "$PKG_DIR/__main__.py"
cp "$HERE/patches/shelves.py"      "$PKG_DIR/shelves.py"
cp "$HERE/patches/rss_shelves.py"  "$PKG_DIR/rss_shelves.py"
cp "$HERE/patches/csv_output.py"   "$PKG_DIR/csv_output.py"

echo "→ Verifying CLI is on PATH..."
command -v goodreads-user-scraper >/dev/null || {
  echo "  ⚠️  goodreads-user-scraper not found on PATH. Make sure your pip's bin dir is in PATH." >&2
  exit 2
}

echo
echo "✅ Installed. Run:"
echo "   $HERE/goodreads-user-scraper.sh <user_id>"
