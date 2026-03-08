"""
IFOP scraper.
URL: https://www.ifop.com/page/{N}/?s&search_formats[0]=post
~592 pages, 12 items per page.
"""
import logging
import time
from .base import get_soup, save_polls

log = logging.getLogger("ifop")

BASE_URL = "https://www.ifop.com/page/{page}/?s&search_formats%5B0%5D=post"


def scrape(max_pages=600):
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
        articles = soup.select("article, .search-result-item, .post-item")

        if not articles:
            # Try alternative selectors for the search results page
            articles = soup.find_all("a", href=True)
            articles = [a for a in articles if a.find("h3") or a.find("h2")]

        if not articles:
            log.info(f"No articles found on page {page}, stopping")
            break

        for article in articles:
            try:
                # Try to find the link
                link_tag = article if article.name == "a" else article.find("a", href=True)
                if not link_tag or "href" not in link_tag.attrs:
                    continue
                link = link_tag["href"]

                # Skip non-article links
                if not link.startswith("https://www.ifop.com/") or link.endswith("/?s&"):
                    continue

                # Find the title
                title_tag = article.find(["h3", "h2"])
                if not title_tag:
                    continue
                subject = title_tag.get_text(strip=True)

                # Find the date
                date_tag = article.find("time") or article.find("date")
                date = date_tag.get_text(strip=True) if date_tag else ""

                if subject:
                    polls.append((date, subject, link))
            except Exception as e:
                log.debug(f"Error parsing article on page {page}: {e}")

        log.info(f"Page {page}: {len(articles)} items found, {len(polls)} total")
        page += 1
        time.sleep(1)

    return save_polls(polls, "IFOP")


if __name__ == "__main__":
    scrape()
