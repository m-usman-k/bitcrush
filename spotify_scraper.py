from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def get_all_tracks(artist_url: str):
    """
    Scrapes the Spotify artist's singles page to get all tracks.

    Args:
        artist_url (str): The URL of the Spotify artist page.

    Returns:
        list: A list of tuples, where each tuple contains (track_name, track_url).
              Returns an empty list if no tracks are found or an error occurs.
    """
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")  # Suppress console logs

    # Initialize the WebDriver
    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        # Open the Spotify artist's singles page
        discography_url = f"{artist_url}/discography/single"
        driver.get(discography_url)
        
        # Wait for the initial tracklist to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="tracklist-row"]'))
        )
        
        # Scroll to load all tracks
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for new content to load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Create BeautifulSoup object from page source
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        tracks = []
        track_rows = soup.find_all('div', attrs={'data-testid': 'tracklist-row'})

        for row in track_rows:
            link_tag = row.find('a', href=lambda x: x and '/track/' in x)
            if link_tag:
                track_name = link_tag.get_text(strip=True)
                track_href = link_tag.get('href')
                full_track_url = f"https://open.spotify.com{track_href}"

                if not track_name:
                    div_with_name = link_tag.find('div')
                    if div_with_name:
                        track_name = div_with_name.get_text(strip=True)

                if track_name and full_track_url:
                    tracks.append((track_name, full_track_url))
        
        return tracks

    except Exception as e:
        print(f"An error occurred while scraping Spotify: {e}")
        return []
    finally:
        if driver:
            driver.quit()