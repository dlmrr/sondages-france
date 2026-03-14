"""
Cluster17 scraper.
Uses WordPress REST API: https://cluster17.com/wp-json/wp/v2/posts
~240 posts total, all categories included.
"""
import logging
import sys
import time
import requests
from .base import HEADERS, save_polls, load_existing_links, append_polls

log = logging.getLogger("cluster17")

API_URL = "https://cluster17.com/wp-json/wp/v2/posts"
COLUMNS = ["date", "subject", "link"]
PER_PAGE = 100


def _fetch_page(page=1):
    """Fetch a page of posts from the WP REST API."""
    params = {
        "per_page": PER_PAGE,
        "page": page,
        "_fields": "title,link,date",
    }
    try:
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        log.warning(f"Failed to fetch page {page}: {e}")
        return None


def scrape(max_pages=10):
    polls = []
    page = 1

    while page <= max_pages:
        data = _fetch_page(page)
        if not data:
            break

        for post in data:
            title = post.get("title", {}).get("rendered", "")
            link = post.get("link", "")
            date = post.get("date", "")[:10]  # YYYY-MM-DD
            if title:
                polls.append((date, title, link))

        print(f"  [CLUSTER17] Page {page}: {len(data)} items | {len(polls)} total")
        sys.stdout.flush()

        if len(data) < PER_PAGE:
            break

        page += 1
        time.sleep(1)

    return save_polls(polls, "CLUSTER17", columns=COLUMNS)


def update(max_pages=3):
    """Incremental update: fetch newest posts, stop when hitting known data."""
    known_links = load_existing_links("CLUSTER17")
    if not known_links:
        print("  [CLUSTER17] No existing data, running full scrape")
        return scrape()

    new_polls = []
    page = 1
    known_streak = 0

    while page <= max_pages:
        data = _fetch_page(page)
        if not data:
            break

        page_new = 0
        for post in data:
            link = post.get("link", "")

            if link in known_links:
                known_streak += 1
                if known_streak >= 3:
                    print(f"  [CLUSTER17] Found 3 known polls in a row, stopping")
                    added = append_polls(new_polls, "CLUSTER17", columns=COLUMNS)
                    print(f"  [CLUSTER17] Added {added} new polls")
                    return added
                continue

            known_streak = 0
            title = post.get("title", {}).get("rendered", "")
            date = post.get("date", "")[:10]
            if title:
                new_polls.append((date, title, link))
                page_new += 1

        print(f"  [CLUSTER17] Page {page}: {page_new} new | {len(new_polls)} total new")
        sys.stdout.flush()
        page += 1
        time.sleep(1)

    added = append_polls(new_polls, "CLUSTER17", columns=COLUMNS)
    print(f"  [CLUSTER17] Added {added} new polls")
    return added


if __name__ == "__main__":
    scrape()
