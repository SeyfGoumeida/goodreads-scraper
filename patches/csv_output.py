import csv
import json
import os
from argparse import Namespace


EXPORT_COLUMNS = [
    "Book Id",
    "Title",
    "Author",
    "Author l-f",
    "Additional Authors",
    "ISBN",
    "ISBN13",
    "My Rating",
    "Publisher",
    "Binding",
    "Number of Pages",
    "Year Published",
    "Original Publication Year",
    "Date Read",
    "Date Added",
    "Bookshelves",
    "Bookshelves with positions",
    "Exclusive Shelf",
    "My Review",
    "Spoiler",
    "Private Notes",
    "Read Count",
    "Owned Copies",
]


def _merge(csv_row, book_json):
    out = dict(csv_row)
    if book_json:
        if book_json.get("book_title"):
            out["Title"] = book_json["book_title"]
        author = book_json.get("author") or {}
        if author.get("author_name"):
            out["Author"] = author["author_name"]
        if book_json.get("num_pages") is not None:
            out["Number of Pages"] = book_json["num_pages"]
        if book_json.get("year_first_published"):
            out["Original Publication Year"] = book_json["year_first_published"]
    return {col: (out.get(col) if out.get(col) is not None else "") for col in EXPORT_COLUMNS}


def _author_lf(name: str) -> str:
    name = (name or "").strip()
    if not name or "," in name:
        return name
    parts = name.split()
    if len(parts) < 2:
        return name
    return parts[-1] + ", " + " ".join(parts[:-1])


def _row_from_json(book_json):
    """Build a CSV row from a book JSON that has _rss metadata (RSS-driven mode)."""
    rss = book_json.get("_rss") or {}
    rating = book_json.get("rating")
    dates_read = book_json.get("dates_read") or []
    shelves = book_json.get("shelves") or []
    exclusive = rss.get("exclusive_shelf") or next(
        (s for s in shelves if s in {"read", "to-read", "currently-reading", "did-not-finish"}),
        "",
    )
    custom_shelves = [s for s in shelves if s not in {"read", "to-read", "currently-reading", "did-not-finish"}]
    author_name = (book_json.get("author") or {}).get("author_name") or rss.get("author_name", "")
    return {
        "Book Id": book_json.get("book_id", ""),
        "Title": book_json.get("book_title", ""),
        "Author": author_name,
        "Author l-f": _author_lf(author_name),
        "Additional Authors": "",
        "ISBN": rss.get("isbn", ""),
        "ISBN13": "",
        "My Rating": str(rating) if rating is not None else "0",
        "Publisher": "",
        "Binding": "",
        "Number of Pages": book_json.get("num_pages") if book_json.get("num_pages") is not None else "",
        "Year Published": "",
        "Original Publication Year": book_json.get("year_first_published") or rss.get("book_published", ""),
        "Date Read": dates_read[0] if dates_read else "",
        "Date Added": rss.get("user_date_added", ""),
        "Bookshelves": ", ".join(custom_shelves),
        "Bookshelves with positions": "",
        "Exclusive Shelf": exclusive,
        "My Review": rss.get("user_review", ""),
        "Spoiler": "",
        "Private Notes": "",
        "Read Count": "1" if exclusive == "read" else "0",
        "Owned Copies": "0",
    }


def write_export_csv(args: Namespace):
    output_csv = getattr(args, "output_csv", None)
    if not output_csv:
        return

    csv_path = getattr(args, "csv_path", None)
    books_dir = args.output_dir + "books/"
    out_rows = []

    if csv_path:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            book_id = (row.get("Book Id") or "").strip()
            book_json = None
            if book_id:
                json_path = books_dir + book_id + ".json"
                if os.path.exists(json_path):
                    with open(json_path, "r") as fh:
                        book_json = json.load(fh)
            out_rows.append(_merge(row, book_json))
    else:
        if not os.path.isdir(books_dir):
            print("⚠️  No books directory at " + books_dir + " — nothing to export")
            return
        for fname in sorted(os.listdir(books_dir)):
            if not fname.endswith(".json"):
                continue
            with open(books_dir + fname, "r") as fh:
                book_json = json.load(fh)
            out_rows.append({col: (v if v is not None else "") for col, v in _row_from_json(book_json).items()})

    os.makedirs(os.path.dirname(os.path.abspath(output_csv)) or ".", exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(out_rows)

    print("📄 Wrote " + str(len(out_rows)) + " rows to " + output_csv)
