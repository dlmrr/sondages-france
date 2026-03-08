"""
IPSOS scraper.
URL: https://www.ipsos.com/fr-fr/insights-hub?type=survey&page={N}
Cards: div.list-item with topic, type, title, teaser, date, link.
Plain requests works — no Selenium needed.
"""
import logging
import random
import sys
import time
from .base import get_soup, save_polls

log = logging.getLogger("ipsos")

BASE_URL = "https://www.ipsos.com/fr-fr/insights-hub?type=survey&page={page}"
COLUMNS = ["date", "subject", "topic", "type", "excerpt", "link"]


def scrape(max_pages=60):
    polls = []
    page = 1
    consecutive_failures = 0

    while page <= max_pages:
        url = BASE_URL.format(page=page)
        soup = get_soup(url)

        if soup is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print(f"  [IPSOS] Stopping after {consecutive_failures} consecutive failures at page {page}")
                break
            page += 1
            continue

        consecutive_failures = 0
        items = soup.select("div.list-item")

        if not items:
            print(f"  [IPSOS] No items on page {page}, stopping")
            break

        for item in items:
            try:
                # Title and link
                title_tag = item.select_one("h3.list-item__title a")
                if not title_tag:
                    continue
                href = title_tag.get("href", "")
                link = href if href.startswith("http") else "https://www.ipsos.com" + href
                subject = title_tag.get_text(strip=True)

                # Date
                time_tag = item.select_one(".list-item__date time")
                date = time_tag.get("datetime", time_tag.get_text(strip=True)) if time_tag else ""

                # Topic
                topic_tag = item.select_one(".list-item__topic a")
                topic = topic_tag.get_text(strip=True) if topic_tag else ""

                # Type (Enquête, etc.)
                type_tag = item.select_one(".list-item__type")
                pub_type = type_tag.get_text(strip=True) if type_tag else ""

                # Excerpt/teaser
                teaser_tag = item.select_one(".list-item__teaser")
                excerpt = teaser_tag.get_text(strip=True) if teaser_tag else ""

                if subject:
                    polls.append((date, subject, topic, pub_type, excerpt, link))
            except Exception as e:
                log.debug(f"Error parsing item on page {page}: {e}")

        print(f"  [IPSOS] Page {page}/{max_pages}: {len(items)} items | {len(polls)} total")
        sys.stdout.flush()

        if page % 10 == 0:
            save_polls(polls, "IPSOS", columns=COLUMNS)

        page += 1
        delay = random.uniform(1.5, 3.0)
        time.sleep(delay)

    return save_polls(polls, "IPSOS", columns=COLUMNS)


if __name__ == "__main__":
    scrape()
