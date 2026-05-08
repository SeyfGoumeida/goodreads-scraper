# goodreads-scraper

Wrapper + patches around [goodreads-user-scraper](https://pypi.org/project/goodreads-user-scraper/) that scrapes a Goodreads user's full library from public endpoints — no login required — and produces a CSV in the exact format of `goodreads_library_export.csv`.

## Why patches?

Since 2024–2025, Goodreads serves a **login wall** on the HTML shelf pages (`/review/list/<user_id>?shelf=…`) the upstream package depends on. Calls fail with:

```text
AttributeError: 'NoneType' object has no attribute 'findChildren'
```

These patches:

1. Replace the broken HTML shelf scrape with the **public RSS feed** at `/review/list_rss/<id>?shelf=…`, which is still un-gated and returns 100 items per page with full per-user data (rating, dates, ISBN, review).
2. Add `--csv_path` to drive shelves from a Goodreads CSV export instead (alternative path for users who'd rather export their library and avoid scraping the rest of book metadata).
3. Add `--output_csv` to produce a single CSV in the exact 23-column format of `goodreads_library_export.csv`.

## Install

```bash
./install.sh
```

This pip-installs `goodreads-user-scraper` and copies the four patched modules from `patches/` over the package files.

## Usage

### Default (RSS-driven, no login, no input CSV)

```bash
./goodreads-user-scraper.sh <user_id>
```

`<user_id>` accepts either form:

- `12345678-jane-doe` (slug, as it appears in the profile URL)
- `12345678` (just the numeric prefix)

Output goes to `~/Downloads/goodreads-data/<user_id>/`:

```text
library.csv        ← single CSV, goodreads_library_export.csv format
books/<id>.json    ← one rich JSON per book (description, genres, ratings, author bio)
```

### With a custom output dir

```bash
./goodreads-user-scraper.sh <user_id> /path/to/output
```

### CSV-driven mode (skip RSS, use an export)

If you already have a Goodreads CSV export and prefer to drive from it:

```bash
GOODREADS_CSV=/path/to/goodreads_library_export.csv ./goodreads-user-scraper.sh <user_id>
```

The shell script forwards this as `--csv_path`. Useful when the RSS feed is rate-limited or when you want richer columns (Publisher, Binding, ISBN13) that the export has but RSS doesn't.

## Output CSV columns

All 23 columns of `goodreads_library_export.csv`. RSS-driven runs leave these blank because they're not in the feed: `ISBN13`, `Publisher`, `Binding`, `Year Published` (the edition year — `Original Publication Year` is filled), `Spoiler`, `Private Notes`, `Owned Copies`. Everything else is populated.

## Files

```text
.
├── README.md
├── install.sh                  - one-shot installer (pip + patch)
├── goodreads-user-scraper.sh   - thin wrapper around the patched CLI
└── patches/
    ├── __main__.py             - adds --csv_path and --output_csv flags
    ├── shelves.py              - routes to RSS or CSV mode
    ├── rss_shelves.py          - new: paginates public RSS feeds
    └── csv_output.py           - new: writes single CSV in export format
```

## Constraints

- The RSS feed is public for any user whose profile is public. Private profiles return an empty/error feed.
- Each book is enriched by hitting `/book/show/<id>` (public). Plan ~3 seconds per book; a 300-book library takes ~15 minutes.
- This relies on Goodreads' public RSS endpoint continuing to exist. If it gets gated like the HTML pages did, the only fallbacks are CSV-driven mode or session-cookie auth (not implemented).

## Re-applying after package upgrade

If `pip install --upgrade goodreads-user-scraper` overwrites the package files, just re-run `./install.sh` to copy the patches back.
