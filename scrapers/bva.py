"""
BVA (now BVA Xsight) scraper.
URL: https://www.bva-xsight.com/sondages/page/{N}/
Paginated with "Suivant" button. Cards with date, category, title.
"""
import logging
import time
from .base import get_soup, save_polls

log = logging.getLogger("bva")

BASE_URL = "https://www.bva-xsight.com/sondages/page/{page}/"


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

        # Try the old bva-group selectors and new xsight selectors
        articles = soup.find_all("div", class_="bva-card-container")
        if not articles:
            articles = soup.find_all("article")
        if not articles:
            # Try generic card patterns
            articles = soup.select(".card, .post-item, .sondage-item")

        if not articles:
            log.info(f"No articles found on page {page}, stopping")
            break

        for article in articles:
            try:
                link_tag = article.find("a", href=True)
                if not link_tag:
                    continue
                link = link_tag["href"]

                title_tag = article.find(["h3", "h2"])
                subject = title_tag.get_text(strip=True) if title_tag else ""

                time_tag = article.find("time")
                date = time_tag.get_text(strip=True) if time_tag else ""
                if not date:
                    date_span = article.find("span", class_="date")
                    date = date_span.get_text(strip=True) if date_span else ""

                if subject:
                    polls.append((date, subject, link))
            except Exception as e:
                log.debug(f"Error parsing article on page {page}: {e}")

        log.info(f"Page {page}: {len(articles)} items found, {len(polls)} total")
        page += 1
        time.sleep(1)

    return save_polls(polls, "BVA")


if __name__ == "__main__":
    scrape()
