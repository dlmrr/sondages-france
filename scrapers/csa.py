"""
CSA scraper.
URL: https://csa.eu/news/page/{N}/
Filters for "- Etude" in article text. Site has been restructured.
"""
import logging
import time
from .base import get_soup, save_polls

log = logging.getLogger("csa")

BASE_URL = "https://csa.eu/news/page/{page}/"


def scrape(max_pages=100):
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

        # Try old structure
        items_found = False
        for a_tag in soup.find_all("a", href=True):
            news_div = a_tag.find("div", class_="c-single-news")
            if news_div:
                text = a_tag.get_text()
                # Only keep études (polls/studies)
                if "Etude" in text or "étude" in text.lower() or "sondage" in text.lower():
                    try:
                        date_tag = a_tag.find("span", class_="date")
                        date = date_tag.get_text(strip=True) if date_tag else ""
                        title_tag = a_tag.find("p", class_="c-single-news_title")
                        subject = title_tag.get_text(strip=True) if title_tag else ""
                        link = a_tag["href"]
                        if subject:
                            polls.append((date, subject, link))
                            items_found = True
                    except Exception as e:
                        log.debug(f"Error parsing news item: {e}")

        # Also try generic article selectors
        if not items_found:
            articles = soup.find_all("article")
            for article in articles:
                try:
                    link_tag = article.find("a", href=True)
                    if not link_tag:
                        continue
                    link = link_tag["href"]
                    title_tag = article.find(["h2", "h3"])
                    subject = title_tag.get_text(strip=True) if title_tag else ""
                    time_tag = article.find("time") or article.find("span", class_="date")
                    date = time_tag.get_text(strip=True) if time_tag else ""
                    if subject:
                        polls.append((date, subject, link))
                        items_found = True
                except Exception as e:
                    log.debug(f"Error parsing article: {e}")

        if not items_found:
            log.info(f"No items found on page {page}, stopping")
            break

        log.info(f"Page {page}: {len(polls)} total polls")
        page += 1
        time.sleep(1)

    return save_polls(polls, "CSA")


if __name__ == "__main__":
    scrape()
