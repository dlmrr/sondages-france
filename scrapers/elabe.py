"""
ELABE scraper.
URL: https://elabe.fr/category/etudes-sondages/page/{N}/
~167 pages, article cards with date/title/link.
"""
import logging
import time
from .base import get_soup, save_polls

log = logging.getLogger("elabe")

BASE_URL = "https://elabe.fr/category/etudes-sondages/page/{page}/"


def scrape(max_pages=200):
    polls = []
    page = 1
    consecutive_failures = 0

    while page <= max_pages:
        url = BASE_URL.format(page=page)
        soup = get_soup(url)

        if soup is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                log.info(f"Stopping after {consecutive_failures} consecutive failures at page {page}")
                break
            page += 1
            continue

        consecutive_failures = 0

        # Try multiple selectors for article cards
        articles = soup.find_all("div", class_="articlebox")
        if not articles:
            articles = soup.find_all("article")

        if not articles:
            log.info(f"No articles found on page {page}, stopping")
            break

        for article in articles:
            try:
                # Title and link
                title_tag = article.find("a", class_="entry-title")
                if not title_tag:
                    title_tag = article.find("a", href=True)
                if not title_tag:
                    continue

                subject = title_tag.get("title") or title_tag.get_text(strip=True)
                link = title_tag["href"]

                # Date
                time_tag = article.find("time")
                date = time_tag.get("datetime", time_tag.get_text(strip=True)) if time_tag else ""

                if subject:
                    polls.append((date, subject, link))
            except Exception as e:
                log.debug(f"Error parsing article on page {page}: {e}")

        log.info(f"Page {page}: {len(articles)} items found, {len(polls)} total")
        page += 1
        time.sleep(1)

    return save_polls(polls, "ELABE")


if __name__ == "__main__":
    scrape()
