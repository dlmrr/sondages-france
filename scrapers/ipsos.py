"""
IPSOS scraper.
URL: https://www.ipsos.com/fr-fr/search?search=fiche+technique&sort_by=created&sort_order=DESC&page={N}
JS-heavy — needs Selenium. ~989 pages originally.
"""
import logging
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import make_driver, save_polls

log = logging.getLogger("ipsos")

BASE_URL = "https://www.ipsos.com/fr-fr/search?search=fiche+technique&sort_by=created&sort_order=DESC&page={page}"


def scrape(max_pages=1000):
    driver = make_driver(headless=True)
    polls = []
    consecutive_failures = 0

    try:
        for page in range(0, max_pages):
            url = BASE_URL.format(page=page)
            try:
                driver.get(url)
                time.sleep(2)

                # Wait for search results to load
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".search-list, .views-row, article"))
                    )
                except Exception:
                    pass

                soup = BeautifulSoup(driver.page_source, "lxml")

                # Try old selector
                results_list = soup.find("ul", class_="search-list")
                items = results_list.find_all("li") if results_list else []

                if not items:
                    # Try alternative selectors
                    items = soup.select(".views-row, .search-result, article")

                if not items:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        log.info(f"Stopping after {consecutive_failures} consecutive empty pages at page {page}")
                        break
                    continue

                consecutive_failures = 0

                for item in items:
                    try:
                        title_tag = item.find(["h2", "h3"])
                        if not title_tag:
                            continue
                        link_tag = title_tag.find("a", href=True) or item.find("a", href=True)
                        if not link_tag:
                            continue

                        href = link_tag["href"]
                        link = href if href.startswith("http") else "https://www.ipsos.com" + href
                        subject = link_tag.get_text(strip=True)

                        time_tag = item.find("time")
                        date = time_tag.get("datetime", time_tag.get_text(strip=True)) if time_tag else ""

                        if subject:
                            polls.append((date, subject, link))
                    except Exception as e:
                        log.debug(f"Error parsing item on page {page}: {e}")

                log.info(f"Page {page}: {len(items)} items, {len(polls)} total")

            except Exception as e:
                log.warning(f"Error loading page {page}: {e}")
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    break

            time.sleep(1.5)
    finally:
        driver.quit()

    return save_polls(polls, "IPSOS")


if __name__ == "__main__":
    scrape()
