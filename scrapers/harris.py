"""
Harris Interactive scraper (now Toluna).
URL: https://tolunacorporate.com/fr/enquetes-publiees/
All ~300 items load on a single page. No pagination.
Cards: article with h6.entry-title, time.entry-date, link.
"""
import logging
import sys
from .base import get_soup, save_polls, load_existing_links, append_polls

log = logging.getLogger("harris")

URL = "https://tolunacorporate.com/fr/enquetes-publiees/"
COLUMNS = ["date", "subject", "link"]


def scrape():
    print("  [HARRIS] Fetching page...")
    sys.stdout.flush()

    soup = get_soup(URL)
    if soup is None:
        print("  [HARRIS] Failed to fetch page")
        return None

    articles = soup.find_all("article")
    print(f"  [HARRIS] Found {len(articles)} articles")
    sys.stdout.flush()

    polls = []
    for article in articles:
        try:
            title_tag = article.find("h6", class_="entry-title")
            if not title_tag:
                title_tag = article.find(["h2", "h3", "h4", "h5", "h6"])
            if not title_tag:
                continue

            link_tag = title_tag.find("a", href=True)
            if not link_tag:
                link_tag = article.find("a", href=True)
            link = link_tag["href"] if link_tag else ""
            subject = link_tag.get_text(strip=True) if link_tag else title_tag.get_text(strip=True)

            time_tag = article.find("time", class_="entry-date")
            if not time_tag:
                time_tag = article.find("time")
            date = time_tag.get("datetime", time_tag.get_text(strip=True)) if time_tag else ""

            if subject:
                polls.append((date, subject, link))
        except Exception as e:
            log.debug(f"Error parsing article: {e}")

    print(f"  [HARRIS] Parsed {len(polls)} polls")
    sys.stdout.flush()

    return save_polls(polls, "HARRIS INTERACTIVE", columns=COLUMNS)


def update():
    """Incremental update: re-scrape the single page and append new polls."""
    print("  [HARRIS] Fetching page for update...")
    sys.stdout.flush()

    soup = get_soup(URL)
    if soup is None:
        print("  [HARRIS] Failed to fetch page")
        return 0

    articles = soup.find_all("article")
    new_polls = []
    for article in articles:
        try:
            title_tag = article.find("h6", class_="entry-title")
            if not title_tag:
                title_tag = article.find(["h2", "h3", "h4", "h5", "h6"])
            if not title_tag:
                continue
            link_tag = title_tag.find("a", href=True)
            if not link_tag:
                link_tag = article.find("a", href=True)
            link = link_tag["href"] if link_tag else ""
            subject = link_tag.get_text(strip=True) if link_tag else title_tag.get_text(strip=True)
            time_tag = article.find("time", class_="entry-date")
            if not time_tag:
                time_tag = article.find("time")
            date = time_tag.get("datetime", time_tag.get_text(strip=True)) if time_tag else ""
            if subject:
                new_polls.append((date, subject, link))
        except Exception as e:
            log.debug(f"Error parsing article: {e}")

    added = append_polls(new_polls, "HARRIS INTERACTIVE", columns=COLUMNS)
    print(f"  [HARRIS] Added {added} new polls")
    return added


if __name__ == "__main__":
    scrape()
