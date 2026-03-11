"""
ODOXA scraper.
URL: https://www.odoxa.fr/les-sondages/
All items load on a single page (JS-rendered). ~2200+ items.
Cards: a.sondage with category, date, title, link.
"""
import logging
import sys
import time
from bs4 import BeautifulSoup
from .base import make_driver, save_polls, append_polls

log = logging.getLogger("odoxa")

URL = "https://www.odoxa.fr/les-sondages/"
COLUMNS = ["date", "subject", "category", "link"]


def scrape():
    print("  [ODOXA] Loading page (all items load at once via JS)...")
    sys.stdout.flush()

    driver = make_driver(headless=True)

    try:
        driver.get(URL)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "lxml")
        sondages = soup.find_all("a", class_="sondage")
        print(f"  [ODOXA] Found {len(sondages)} items on page")
        sys.stdout.flush()

        polls = []
        for item in sondages:
            try:
                link = item.get("href", "")

                date_tag = item.find("span", class_="date")
                date = date_tag.get_text(strip=True) if date_tag else ""

                title_tag = item.find("h2")
                subject = title_tag.get_text(strip=True) if title_tag else ""

                cat_span = item.find("span", class_="category")
                category = cat_span.get_text(strip=True) if cat_span else ""

                if subject:
                    polls.append((date, subject, category, link))
            except Exception as e:
                log.debug(f"Error parsing item: {e}")

        print(f"  [ODOXA] Parsed {len(polls)} polls")
        sys.stdout.flush()

    finally:
        driver.quit()

    return save_polls(polls, "ODOXA", columns=COLUMNS)


def update():
    """Incremental update: re-scrape the single page and append new polls."""
    print("  [ODOXA] Loading page for update...")
    sys.stdout.flush()

    driver = make_driver(headless=True)
    try:
        driver.get(URL)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "lxml")
        sondages = soup.find_all("a", class_="sondage")
        print(f"  [ODOXA] Found {len(sondages)} items")
        sys.stdout.flush()

        new_polls = []
        for item in sondages:
            try:
                link = item.get("href", "")
                date_tag = item.find("span", class_="date")
                date = date_tag.get_text(strip=True) if date_tag else ""
                title_tag = item.find("h2")
                subject = title_tag.get_text(strip=True) if title_tag else ""
                cat_span = item.find("span", class_="category")
                category = cat_span.get_text(strip=True) if cat_span else ""
                if subject:
                    new_polls.append((date, subject, category, link))
            except Exception as e:
                log.debug(f"Error parsing item: {e}")
    finally:
        driver.quit()

    added = append_polls(new_polls, "ODOXA", columns=COLUMNS)
    print(f"  [ODOXA] Added {added} new polls")
    return added


if __name__ == "__main__":
    scrape()
