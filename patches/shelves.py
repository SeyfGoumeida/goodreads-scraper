from argparse import Namespace
import csv
import json
from urllib.request import urlopen
import os
from bs4 import BeautifulSoup
import re

from scraper import books


RATING_STARS_DICT = {
    "it was amazing": 5,
    "really liked it": 4,
    "liked it": 3,
    "it was ok": 2,
    "did not like it": 1,
    "": None,
}


def _parse_shelves_from_row(row):
    shelves = []
    exclusive = (row.get("Exclusive Shelf") or "").strip()
    if exclusive:
        shelves.append(exclusive)
    bookshelves_field = (row.get("Bookshelves") or "").strip()
    if bookshelves_field:
        for s in bookshelves_field.split(","):
            s = s.strip()
            if s and s not in shelves:
                shelves.append(s)
    return shelves


def _parse_rating_from_row(row):
    raw = (row.get("My Rating") or "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if 1 <= n <= 5 else None


def _parse_dates_read_from_row(row):
    date_read = (row.get("Date Read") or "").strip()
    return [date_read] if date_read else []


def get_all_shelves_from_csv(args: Namespace):
    csv_path: str = args.csv_path
    output_dir: str = args.output_dir + "books/"
    os.makedirs(output_dir, exist_ok=True)

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    shelves_to_rows: dict = {}
    for row in rows:
        for shelf in _parse_shelves_from_row(row):
            shelves_to_rows.setdefault(shelf, []).append(row)

    for shelf, shelf_rows in shelves_to_rows.items():
        print("Scraping '" + shelf + "' shelf...")
        for row in shelf_rows:
            book_id = (row.get("Book Id") or "").strip()
            if not book_id:
                continue
            file_path = output_dir + book_id + ".json"

            if os.path.exists(file_path):
                with open(file_path, "r") as fh:
                    book = json.load(fh)
                if shelf not in book.get("shelves", []):
                    book.setdefault("shelves", []).append(shelf)
                    with open(file_path, "w") as fh:
                        json.dump(book, fh, indent=2)
                    print("✅ Updated " + book_id)
                continue

            try:
                book = books.scrape_book(book_id, args)
            except Exception as e:
                print("⚠️  Failed to scrape " + book_id + ": " + repr(e))
                continue
            book["rating"] = _parse_rating_from_row(row)
            book["dates_read"] = _parse_dates_read_from_row(row)
            book["shelves"] = [shelf]
            with open(file_path, "w") as fh:
                json.dump(book, fh, indent=2)
            print("🎉 Scraped " + book_id)
        print()


def get_shelf_url(user_id, shelf, page):
    url = (
        "https://www.goodreads.com/review/list/"
        + user_id
        + "?shelf="
        + shelf
        + "&page="
        + str(page)
        + "&print=true"
    )
    source = urlopen(url)
    return BeautifulSoup(source, "html.parser")


def get_id(book_row):
    cell = book_row.find("td", {"class": "field title"})
    title_href = cell.find("div", {"class": "value"}).find("a")
    return title_href.attrs.get("href").split("/")[-1]


def get_rating(book_row):
    cell = book_row.find("td", {"class": "field rating"})
    str_rating = cell.find("div", {"class": "value"}).find("span").attrs.get("title")
    return RATING_STARS_DICT.get(str_rating)


def get_dates_read(book_row):
    cell = book_row.find("td", {"class": "field date_read"})
    dates = cell.find("div", {"class": "value"}).findChildren(
        "div", {"class": "date_row"}
    )
    date_arr = []
    for date in dates:
        date_text = date.text.strip()
        if date_text != "not set":
            date_arr += [date_text]
    return date_arr


def get_shelf(args: Namespace, shelf: str):
    print("Scraping '" + shelf + "' shelf...")
    user_id: str = args.user_id
    output_dir: str = args.output_dir + "books/"
    page = 1

    while True:
        soup = get_shelf_url(user_id, shelf, page)

        no_content = soup.find("div", {"class": "greyText nocontent stacked"})
        if no_content:
            break

        books_table = soup.find("tbody", {"id": "booksBody"})
        book_rows = books_table.findChildren("tr", recursive=False)

        # Loop through all books in the page
        for book_row in book_rows:
            book_id = get_id(book_row)
            file_path = output_dir + book_id + ".json"

            book = None
            changed = False

            # If the book has already been scraped, just add the shelf
            if os.path.exists(file_path):
                file = open(file_path, "r")
                book = json.load(file)
                if shelf not in book["shelves"]:
                    book["shelves"].append(shelf)
                    print("✅ Updated " + book_id)
                    changed = True
                file.close()
            # If not already scraped, scrape the book and add the shelf
            else:
                book = books.scrape_book(book_id, args)
                book["rating"] = get_rating(book_row)
                book["dates_read"] = get_dates_read(book_row)
                book["shelves"] = [shelf]
                print("🎉 Scraped " + book_id)
                changed = True

            if changed:
                # Write the json file for the book
                file = open(file_path, "w")
                json.dump(book, file, indent=2)
                file.close()

        page += 1

    print()


def get_all_shelves(args: Namespace):
    if args.skip_shelves:
        return

    if getattr(args, "csv_path", None):
        get_all_shelves_from_csv(args)
        return

    from scraper import rss_shelves
    rss_shelves.get_all_shelves_via_rss(args)
