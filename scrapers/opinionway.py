"""
OpinionWay scraper.
URL: https://www.opinion-way.com/fr/publications/page/{N}/
~417 pages, 9 items per page. Cards with type, title, link.
No date on listing — extracted from title when possible.
"""
import logging
import random
import re
import sys
import time
from .base import get_soup, save_polls, load_existing_links, append_polls

log = logging.getLogger("opinionway")

BASE_URL = "https://www.opinion-way.com/fr/publications/page/{page}/"
FIRST_PAGE_URL = "https://www.opinion-way.com/fr/sondage-d-opinion/sondages-publies.html"
COLUMNS = ["date", "subject", "type", "link"]

MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}


def extract_date_from_title(title):
    """Extract date from title like '... - Mars 2026' or '... - Février 2026'."""
    text = title.lower().strip()
    for month_name, month_num in MONTHS.items():
        match = re.search(rf"{month_name}\s+(\d{{4}})", text)
        if match:
            year = match.group(1)
            return f"01/{month_num:02d}/{year}"
    # Try just a year
    match = re.search(r"(\d{4})$", text.rstrip())
    if match:
        return f"01/01/{match.group(1)}"
    return ""


def scrape(max_pages=500):
    polls = []
    page = 1
    consecutive_failures = 0

    while page <= max_pages:
        url = FIRST_PAGE_URL if page == 1 else BASE_URL.format(page=page)
        soup = get_soup(url)

        if soup is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print(f"  [OPINIONWAY] Stopping after {consecutive_failures} consecutive failures at page {page}")
                break
            page += 1
            continue

        consecutive_failures = 0
        items = soup.select(".publication--item")

        if not items:
            print(f"  [OPINIONWAY] No items on page {page}, stopping")
            break

        for item in items:
            try:
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                link = link_tag["href"]

                title_tag = item.find(["h3", "h2", "h4"])
                subject = title_tag.get_text(strip=True) if title_tag else ""

                type_tag = item.select_one(".publication--type")
                pub_type = type_tag.get_text(strip=True) if type_tag else ""

                date = extract_date_from_title(subject)

                if subject:
                    polls.append((date, subject, pub_type, link))
            except Exception as e:
                log.debug(f"Error parsing item on page {page}: {e}")

        print(f"  [OPINIONWAY] Page {page}: {len(items)} items | {len(polls)} total")
        sys.stdout.flush()

        if page % 10 == 0:
            save_polls(polls, "OPINION WAY", columns=COLUMNS)

        page += 1
        # Random delay to avoid detection
        delay = random.uniform(1.5, 3.5)
        if page > 1 and (page - 1) % 30 == 0:
            pause = random.uniform(8, 15)
            print(f"  [OPINIONWAY] Taking a {pause:.0f}s break...")
            sys.stdout.flush()
            time.sleep(pause)
        time.sleep(delay)

    return save_polls(polls, "OPINION WAY", columns=COLUMNS)


def update(max_pages=10):
    """Incremental update: fetch only new polls."""
    known_links = load_existing_links("OPINION WAY")
    if not known_links:
        print("  [OPINIONWAY] No existing data, running full scrape")
        return scrape()

    new_polls = []
    page = 1
    known_streak = 0

    while page <= max_pages:
        url = FIRST_PAGE_URL if page == 1 else BASE_URL.format(page=page)
        soup = get_soup(url)
        if soup is None:
            break

        items = soup.select(".publication--item")
        if not items:
            break

        page_new = 0
        for item in items:
            try:
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                link = link_tag["href"]

                if link in known_links:
                    known_streak += 1
                    if known_streak >= 3:
                        print(f"  [OPINIONWAY] Found 3 known polls in a row, stopping")
                        added = append_polls(new_polls, "OPINION WAY", columns=COLUMNS)
                        print(f"  [OPINIONWAY] Added {added} new polls")
                        return added
                    continue

                known_streak = 0
                title_tag = item.find(["h3", "h2", "h4"])
                subject = title_tag.get_text(strip=True) if title_tag else ""
                type_tag = item.select_one(".publication--type")
                pub_type = type_tag.get_text(strip=True) if type_tag else ""
                date = extract_date_from_title(subject)
                if subject:
                    new_polls.append((date, subject, pub_type, link))
                    page_new += 1
            except Exception as e:
                log.debug(f"Error parsing item: {e}")

        print(f"  [OPINIONWAY] Page {page}: {page_new} new | {len(new_polls)} total new")
        sys.stdout.flush()
        page += 1
        time.sleep(random.uniform(1.5, 3.5))

    added = append_polls(new_polls, "OPINION WAY", columns=COLUMNS)
    print(f"  [OPINIONWAY] Added {added} new polls")
    return added


if __name__ == "__main__":
    scrape()
