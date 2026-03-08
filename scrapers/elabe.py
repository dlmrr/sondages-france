"""
ELABE scraper.
URL: https://elabe.fr/category/etudes-sondages/page/{N}/
~167 pages, article cards with date/title/category/tags/excerpt/link.
"""
import logging
import sys
import time
import pandas as pd
from .base import get_soup, save_polls, DATA_DIR

log = logging.getLogger("elabe")

BASE_URL = "https://elabe.fr/category/etudes-sondages/page/{page}/"
COLUMNS = ["date", "subject", "category", "tags", "excerpt", "link"]


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
                print(f"  [ELABE] Stopping after {consecutive_failures} consecutive failures at page {page}")
                break
            page += 1
            continue

        consecutive_failures = 0

        articles = soup.find_all("div", class_="articlebox")
        if not articles:
            articles = soup.find_all("article")

        if not articles:
            print(f"  [ELABE] No articles found on page {page}, stopping")
            break

        for article in articles:
            try:
                # Find the inner <article> tag if we matched the outer div
                inner = article.find("article") or article

                # Title and link
                title_tag = inner.find("a", class_="entry-title")
                if not title_tag:
                    title_tag = inner.find("a", href=True)
                if not title_tag:
                    continue

                subject = title_tag.get("title") or title_tag.get_text(strip=True)
                link = title_tag["href"]

                # Date
                time_tag = inner.find("time")
                date = time_tag.get("datetime", time_tag.get_text(strip=True)) if time_tag else ""

                # Category
                cat_tag = inner.find("a", rel="category tag")
                category = cat_tag.get_text(strip=True) if cat_tag else ""

                # Tags — extracted from article CSS classes like "tag-bfmtv tag-intentions-de-vote"
                css_classes = inner.get("class", [])
                tags = ", ".join(
                    cls.replace("tag-", "").replace("-", " ")
                    for cls in css_classes
                    if cls.startswith("tag-")
                )

                # Excerpt
                excerpt_div = inner.find("div", class_="col-sm-8")
                if excerpt_div:
                    lire_link = excerpt_div.find("a")
                    if lire_link:
                        lire_link.decompose()
                    excerpt = excerpt_div.get_text(strip=True)
                else:
                    excerpt = ""

                if subject:
                    polls.append((date, subject, category, tags, excerpt, link))
            except Exception as e:
                log.debug(f"Error parsing article on page {page}: {e}")

        print(f"  [ELABE] Page {page}: {len(articles)} items | {len(polls)} total")
        sys.stdout.flush()

        # Save incrementally every 10 pages
        if page % 10 == 0:
            save_polls(polls, "ELABE", columns=COLUMNS)

        page += 1
        time.sleep(1)

    return save_polls(polls, "ELABE", columns=COLUMNS)


if __name__ == "__main__":
    scrape()
