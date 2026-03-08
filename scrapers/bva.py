"""
BVA (now BVA Xsight) scraper.
URL: https://www.bva-xsight.com/sondages/page/{N}/
21 items per page. Cards with category, date, title, excerpt, link.
"""
import logging
import sys
import time
from .base import get_soup, save_polls

log = logging.getLogger("bva")

BASE_URL = "https://www.bva-xsight.com/sondages/page/{page}/"
FIRST_PAGE_URL = "https://www.bva-xsight.com/sondages/"
COLUMNS = ["date", "subject", "category", "excerpt", "link"]


def scrape(max_pages=200):
    polls = []
    page = 1
    consecutive_failures = 0

    while page <= max_pages:
        url = FIRST_PAGE_URL if page == 1 else BASE_URL.format(page=page)
        soup = get_soup(url)

        if soup is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print(f"  [BVA] Stopping after {consecutive_failures} consecutive failures at page {page}")
                break
            page += 1
            continue

        consecutive_failures = 0
        cards = soup.find_all("div", class_="bva-card-container")

        if not cards:
            print(f"  [BVA] No cards found on page {page}, stopping")
            break

        for card in cards:
            try:
                link_tag = card.find("a", class_="cover-link")
                if not link_tag:
                    continue
                link = link_tag["href"]

                title_tag = card.find("h3", class_="title")
                subject = title_tag.get_text(strip=True) if title_tag else ""

                time_tag = card.find("time", class_="date")
                date = time_tag.get("datetime", time_tag.get_text(strip=True)) if time_tag else ""

                cat_tag = card.find("span", class_="text-gradient")
                category = cat_tag.get_text(strip=True) if cat_tag else ""

                # Excerpt: get text from <p> tags inside text-container
                text_container = card.find("div", class_="text-container")
                if text_container:
                    paragraphs = text_container.find_all("p")
                    excerpt = " ".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                else:
                    excerpt = ""

                if subject:
                    polls.append((date, subject, category, excerpt, link))
            except Exception as e:
                log.debug(f"Error parsing card on page {page}: {e}")

        print(f"  [BVA] Page {page}: {len(cards)} items | {len(polls)} total")
        sys.stdout.flush()

        if page % 10 == 0:
            save_polls(polls, "BVA", columns=COLUMNS)

        page += 1
        time.sleep(1)

    return save_polls(polls, "BVA", columns=COLUMNS)


if __name__ == "__main__":
    scrape()
