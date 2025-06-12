import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def get_all_tracks(artist_url: str):
    """
    Scrapes the Spotify artist's singles page using Playwright.

    Args:
        artist_url (str): The URL of the Spotify artist page.

    Returns:
        list: A list of tuples, where each tuple contains (track_name, track_url).
              Returns an empty list if no tracks are found or an error occurs.
    """
    async with async_playwright() as p:
        browser = None
        try:
            # Launch the browser. These args are crucial for running in containers.
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            page = await browser.new_page()
            
            # Go to the artist's singles page
            discography_url = f"{artist_url}/discography/single"
            await page.goto(discography_url, wait_until='networkidle', timeout=30000)

            # Wait for the first track row to ensure the page has started loading
            await page.wait_for_selector('div[data-testid="tracklist-row"]', timeout=20000)

            # Scroll to the bottom of the page to load all tracks
            last_height = await page.evaluate('document.body.scrollHeight')
            while True:
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)  # Wait for new content to load
                new_height = await page.evaluate('document.body.scrollHeight')
                if new_height == last_height:
                    break
                last_height = new_height

            # Get the final page content and parse it
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            tracks = []
            track_rows = soup.select('div[data-testid="tracklist-row"]')

            for row in track_rows:
                link_tag = row.select_one('a[href*="/track/"]')
                if link_tag:
                    track_name = link_tag.get_text(strip=True)
                    track_href = link_tag.get('href')
                    
                    # Construct the full, absolute URL
                    if track_href.startswith('/'):
                        full_track_url = f"https://open.spotify.com{track_href}"
                    else:
                        full_track_url = track_href

                    if track_name and full_track_url:
                        tracks.append((track_name, full_track_url))
            
            return tracks

        except Exception as e:
            print(f"An error occurred while scraping Spotify with Playwright: {e}")
            return []
        finally:
            if browser:
                await browser.close()
