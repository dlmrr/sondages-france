"""
OpinionWay scraper.
URL: https://www.opinion-way.com/fr/sondage-d-opinion/sondages-publies.html
JS-heavy with pagination. Old pattern used ?start=N (steps of 30).
"""
import logging
import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import make_driver, save_polls

log = logging.getLogger("opinionway")

BASE_URL = "https://www.opinion-way.com/fr/sondage-d-opinion/sondages-publies.html"

MONTHS = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}


def extract_date_from_title(title):
    """Try to extract a date from the poll title (e.g. '... Mars 2024')."""
    text = title.lower().strip()
    for month_name, month_num in MONTHS.items():
        match = re.search(rf"{month_name}\s+(\d{{4}})$", text)
        if match:
            year = match.group(1)
            return f"01/{month_num:02d}/{year}"
    return ""


def scrape(max_pages=200):
    driver = make_driver(headless=True)
    polls = []

    try:
        # First try the paginated approach with ?start=N
        for start in range(0, max_pages * 30, 30):
            url = f"{BASE_URL}?filter_search=%20&layout=table&show_category=0&start={start}"
            try:
                driver.get(url)
                time.sleep(2)

                soup = BeautifulSoup(driver.page_source, "lxml")

                # Old selector
                items = soup.find_all("td", class_="edocman-document-title-td")
                if not items:
                    # Try alternative selectors
                    items = soup.select(".publication--item, .document-item, article")

                if not items:
                    # Try finding any links in the main content area
                    main = soup.find("main") or soup.find("div", id="content") or soup
                    items = main.find_all("a", href=True)
                    items = [a for a in items if a.find(["h2", "h3", "h4"]) or len(a.get_text(strip=True)) > 20]

                if not items:
                    log.info(f"No items found at start={start}, stopping")
                    break

                for item in items:
                    try:
                        if item.name == "td":
                            link_tag = item.find("a", href=True)
                        elif item.name == "a":
                            link_tag = item
                        else:
                            link_tag = item.find("a", href=True)

                        if not link_tag:
                            continue

                        href = link_tag["href"]
                        link = href if href.startswith("http") else "https://www.opinion-way.com" + href
                        subject = link_tag.get_text(strip=True)

                        # OpinionWay doesn't show dates directly — extract from title
                        date = extract_date_from_title(subject)

                        if subject and len(subject) > 5:
                            polls.append((date, subject, link))
                    except Exception as e:
                        log.debug(f"Error parsing item: {e}")

                log.info(f"Start {start}: {len(items)} items, {len(polls)} total")

            except Exception as e:
                log.warning(f"Error at start={start}: {e}")

            time.sleep(1.5)
    finally:
        driver.quit()

    return save_polls(polls, "OPINION WAY")


if __name__ == "__main__":
    scrape()
