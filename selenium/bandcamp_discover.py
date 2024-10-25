import csv
from itertools import count
from collections import namedtuple
from pathlib import Path
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


SITE = 'https://bandcamp.com/'
EXPECTED_TRACKS_PER_PAGE = 8
CSV_FILE_PATH = Path('tracks.csv')


class DiscoverLocators:
    """CSS and XPath locators for the discover section elements."""
    CAROUSEL_PAGE = 'item-page'
    DISCOVER_BLOCK = 'discover-results'
    DISCOVER_ITEM = 'discover-item'
    DISCOVER_ITEM_TITLE = 'item-title'
    DISCOVER_ITEM_ARTIST = 'item-artist'
    DISCOVER_ITEM_GENRE = 'item-genre'
    NEXT_BTN = "//a[contains(@class, 'item-page') and text()='next']"


class DiscoverGatherer:
    """Handles scraping and storing track information from the Bandcamp discover section."""
    Track = namedtuple('Track', ['id', 'page', 'title', 'artist', 'genre'])

    def __init__(self, site_url, headless=False):
        """Initialize the browser and load the site."""
        options = Options()
        if headless:
            options.add_argument("--headless")
        self.browser = Firefox(options=options)
        self.browser.get(site_url)
        self.wait = WebDriverWait(self.browser, timeout=10)
        # self.db_file = Path('tracks.csv')
        self.file_exists = CSV_FILE_PATH.exists()
        self.locators = DiscoverLocators()

    def get_total_pages(self):
        """Retrieve the total number of pages available in the carousel pagination."""
        try:
            return int(self.browser.find_elements(By.CLASS_NAME, self.locators.CAROUSEL_PAGE)[-2].text)
        except Exception as e:
            print('Error retrieving total pages:', e)
            return 0

    def _collect_track_info(self, visible_tracks, discovery_item_id, page_num):
        """Extract track details from visible track elements."""
        page_tracks = []
        for item in visible_tracks:
            try:
                title = item.find_element(By.CLASS_NAME, self.locators.DISCOVER_ITEM_TITLE).text.strip()
                artist = item.find_element(By.CLASS_NAME, self.locators.DISCOVER_ITEM_ARTIST).text.strip()
                genre = item.find_element(By.CLASS_NAME, self.locators.DISCOVER_ITEM_GENRE).text.strip()
                page_tracks.append(self.Track(next(discovery_item_id), page_num, title, artist, genre))
                print(f"Track '{title}' collected.")
            except Exception as e:
                print(f"Error processing track on page {page_num}: {e}")
        return page_tracks

    def get_tracks(self):
        """Scrape track information from each carousel page and store in a CSV."""
        discovery_item_id = count(1)
        total_pages = self.get_total_pages()
        if total_pages == 0:
            return

        for page_num in range(total_pages):
            discover_section = self.wait.until(
                EC.visibility_of_element_located((By.CLASS_NAME, self.locators.DISCOVER_BLOCK))
            )
            discover_items = discover_section.find_elements(By.CLASS_NAME, self.locators.DISCOVER_ITEM)

            visible_tracks = [item for item in discover_items if item.is_displayed()]
            if len(visible_tracks) != EXPECTED_TRACKS_PER_PAGE:
                print(f"Expected {EXPECTED_TRACKS_PER_PAGE} tracks, but found {len(visible_tracks)} on page {page_num + 1}")
                continue

            page_tracks = self._collect_track_info(visible_tracks, discovery_item_id, page_num + 1)
            self._append_tracks_to_csv(page_tracks)

            next_button = self.browser.find_element(By.XPATH, self.locators.NEXT_BTN)
            next_button.click()

    def _append_tracks_to_csv(self, data):
        """Append track data to the CSV file, adding headers if the file is new."""
        with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8') as f_out:
            writer = csv.writer(f_out)
            if not self.file_exists:
                writer.writerow(self.Track._fields)
                self.file_exists = True
            writer.writerows(data)

    def close(self):
        """Close the browser instance."""
        self.browser.quit()
        print("Browser closed.")


gatherer = DiscoverGatherer(SITE, headless=True)
gatherer.get_tracks()
gatherer.close()
