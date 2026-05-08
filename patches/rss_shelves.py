"""
Scrape a Goodreads user's shelves via the public RSS feeds.

Goodreads gates the HTML shelf pages (/review/list/<id>?shelf=...) behind login
since 2024-2025, but the RSS endpoint at /review/list_rss/<id>?shelf=... remains
public and returns full per-user data: rating, dates, ISBN, review, etc.
"""

from argparse import Namespace
from datetime import datetime
from urllib.request import urlopen, Request
import json
import os
import re
import xml.etree.ElementTree as ET

from scraper import books


STANDARD_SHELVES = ["read", "to-read", "currently-reading", "did-not-finish"]
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
ITEMS_PER_PAGE = 100


def _user_id_numeric(user_id: str) -> str:
    m = re.match(r"^(\d+)", user_id)
    return m.group(1) if m else user_id


def _fetch_xml(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    return urlopen(req).read()


def _parse_items(xml_text: bytes):
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []
    out = []
    for item in channel.findall("item"):
        rec = {}
        for child in item:
            if child.tag == "book":
                np = child.find("num_pages")
                if np is not None and np.text:
                    rec["num_pages"] = np.text.strip()
            else:
                rec[child.tag] = (child.text or "").strip()
        out.append(rec)
    return out


def _format_date(rss_date: str) -> str:
    """RFC822 like 'Wed, 29 Apr 2026 14:45:15 -0700' → 'YYYY/MM/DD'."""
    if not rss_date:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(rss_date, fmt).strftime("%Y/%m/%d")
        except ValueError:
            continue
    return rss_date


def _split_user_shelves(value: str):
    if not value:
        return []
    return [s.strip() for s in re.split(r"[,\s]+", value) if s.strip()]


def iter_shelf_records(user_id: str, shelf: str):
    numeric = _user_id_numeric(user_id)
    page = 1
    while True:
        url = (
            "https://www.goodreads.com/review/list_rss/"
            + numeric
            + "?shelf="
            + shelf
            + "&page="
            + str(page)
        )
        xml_text = _fetch_xml(url)
        items = _parse_items(xml_text)
        if not items:
            return
        for rec in items:
            yield rec
        if len(items) < ITEMS_PER_PAGE:
            return
        page += 1


def collect_all_records(args: Namespace, shelves=STANDARD_SHELVES):
    """Return {book_id: {"rss": dict, "shelves": [..], "exclusive_shelf": str}}."""
    user_id = args.user_id
    by_book = {}
    for shelf in shelves:
        print("Fetching '" + shelf + "' shelf via RSS...")
        count = 0
        for rec in iter_shelf_records(user_id, shelf):
            book_id = rec.get("book_id")
            if not book_id:
                continue
            count += 1
            entry = by_book.setdefault(
                book_id,
                {"rss": rec, "shelves": [], "exclusive_shelf": shelf},
            )
            if shelf not in entry["shelves"]:
                entry["shelves"].append(shelf)
            entry["exclusive_shelf"] = shelf
            for s in _split_user_shelves(rec.get("user_shelves", "")):
                if s not in entry["shelves"]:
                    entry["shelves"].append(s)
        print("  → " + str(count) + " items")
    return by_book


def _rating_or_none(value: str):
    try:
        n = int((value or "0").strip())
    except ValueError:
        return None
    return n if 1 <= n <= 5 else None


def get_all_shelves_via_rss(args: Namespace):
    output_dir = args.output_dir + "books/"
    os.makedirs(output_dir, exist_ok=True)

    by_book = collect_all_records(args)
    print("\nProcessing " + str(len(by_book)) + " unique books...\n")

    for book_id, entry in by_book.items():
        rec = entry["rss"]
        shelves = entry["shelves"]
        file_path = output_dir + book_id + ".json"

        if os.path.exists(file_path):
            with open(file_path, "r") as fh:
                book = json.load(fh)
            changed = False
            for s in shelves:
                if s not in book.get("shelves", []):
                    book.setdefault("shelves", []).append(s)
                    changed = True
            if changed:
                with open(file_path, "w") as fh:
                    json.dump(book, fh, indent=2, ensure_ascii=False)
                print("✅ Updated " + book_id)
            continue

        try:
            book = books.scrape_book(book_id, args)
        except Exception as e:
            print("⚠️  /book/show scrape failed for " + book_id + ": " + repr(e) + " — using RSS data only")
            book = {
                "book_id_title": book_id,
                "book_id": book_id,
                "book_title": rec.get("title", ""),
                "book_url": "https://www.goodreads.com/book/show/" + book_id,
                "book_image": rec.get("book_large_image_url") or rec.get("book_image_url", ""),
                "year_first_published": rec.get("book_published", ""),
                "num_pages": int(rec["num_pages"]) if rec.get("num_pages", "").isdigit() else None,
            }

        book["rating"] = _rating_or_none(rec.get("user_rating"))
        date_read = _format_date(rec.get("user_read_at", ""))
        book["dates_read"] = [date_read] if date_read else []
        book["shelves"] = shelves
        book["_rss"] = {
            "isbn": rec.get("isbn", ""),
            "user_review": rec.get("user_review", ""),
            "user_date_added": _format_date(rec.get("user_date_added", "")),
            "book_published": rec.get("book_published", ""),
            "exclusive_shelf": entry["exclusive_shelf"],
            "user_shelves": rec.get("user_shelves", ""),
            "author_name": rec.get("author_name", ""),
        }

        with open(file_path, "w") as fh:
            json.dump(book, fh, indent=2, ensure_ascii=False)
        print("🎉 Scraped " + book_id)

    print()
