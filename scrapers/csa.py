"""
CSA scraper.
URL: https://csa.eu/news/page/{N}/
~45 pages, 18 items per page. All items are studies/polls.
"""
import logging
import sys
import time
from .base import get_soup, save_polls, load_existing_links, append_polls

log = logging.getLogger("csa")

BASE_URL = "https://csa.eu/news/page/{page}/"
FIRST_PAGE_URL = "https://csa.eu/news/"
COLUMNS = ["date", "subject", "link"]


def scrape(max_pages=100):
    polls = []
    page = 1
    consecutive_failures = 0

    while page <= max_pages:
        url = FIRST_PAGE_URL if page == 1 else BASE_URL.format(page=page)
        soup = get_soup(url)

        if soup is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print(f"  [CSA] Stopping after {consecutive_failures} consecutive failures at page {page}")
                break
            page += 1
            continue

        consecutive_failures = 0

        items = [a for a in soup.find_all("a", href=True) if a.find("div", class_="c-single-news")]

        if not items:
            print(f"  [CSA] No items found on page {page}, stopping")
            break

        for item in items:
            try:
                link = item["href"]

                title_tag = item.find("p", class_="c-single-news_title")
                subject = title_tag.get_text(strip=True) if title_tag else ""

                date_tag = item.find("span", class_="date")
                date = date_tag.get_text(strip=True) if date_tag else ""

                if subject:
                    polls.append((date, subject, link))
            except Exception as e:
                log.debug(f"Error parsing item on page {page}: {e}")

        print(f"  [CSA] Page {page}: {len(items)} items | {len(polls)} total")
        sys.stdout.flush()

        if page % 10 == 0:
            save_polls(polls, "CSA", columns=COLUMNS)

        page += 1
        time.sleep(1)

    return save_polls(polls, "CSA", columns=COLUMNS)


def update(max_pages=10):
    """Incremental update: fetch only new polls."""
    known_links = load_existing_links("CSA")
    if not known_links:
        print("  [CSA] No existing data, running full scrape")
        return scrape()

    new_polls = []
    page = 1
    known_streak = 0

    while page <= max_pages:
        url = FIRST_PAGE_URL if page == 1 else BASE_URL.format(page=page)
        soup = get_soup(url)
        if soup is None:
            break

        items = [a for a in soup.find_all("a", href=True) if a.find("div", class_="c-single-news")]
        if not items:
            break

        page_new = 0
        for item in items:
            try:
                link = item["href"]

                if link in known_links:
                    known_streak += 1
                    if known_streak >= 3:
                        print(f"  [CSA] Found 3 known polls in a row, stopping")
                        added = append_polls(new_polls, "CSA", columns=COLUMNS)
                        print(f"  [CSA] Added {added} new polls")
                        return added
                    continue

                known_streak = 0
                title_tag = item.find("p", class_="c-single-news_title")
                subject = title_tag.get_text(strip=True) if title_tag else ""
                date_tag = item.find("span", class_="date")
                date = date_tag.get_text(strip=True) if date_tag else ""
                if subject:
                    new_polls.append((date, subject, link))
                    page_new += 1
            except Exception as e:
                log.debug(f"Error parsing item: {e}")

        print(f"  [CSA] Page {page}: {page_new} new | {len(new_polls)} total new")
        sys.stdout.flush()
        page += 1
        time.sleep(1)

    added = append_polls(new_polls, "CSA", columns=COLUMNS)
    print(f"  [CSA] Added {added} new polls")
    return added


if __name__ == "__main__":
    scrape()
