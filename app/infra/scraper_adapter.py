import io
import re
import logging
import httpx

logger = logging.getLogger(__name__)

class WebScraper:
    """
    Advanced Networking Infrastructure for scraping files directly from LMS URLs.
    """

    @staticmethod
    async def fetch_h5p_from_link(message_text: str) -> tuple[io.BytesIO, str]:
        """Extracts a URL, applies Moodle exploits, and downloads the binary."""
        logger.info("Initializing Web Scraper Engine...")

        # 1. Regex Pattern to extract the URL from the messy iframe code
        url_match = re.search(r'src="([^"]+)"', message_text)
        if url_match:
            url = url_match.group(1)
        elif message_text.startswith("http"):
            url = message_text
        else:
            raise ValueError("No valid URL found in the text.")

        # 2. The Moodle Exploit: Rewrite 'embed.php' to 'export.php'
        if '/mod/hvp/embed.php' in url:
            url = url.replace('embed.php', 'export.php')
            logger.info(f"Targeting hidden export URL: {url}")

        # 3. Execute the Web Request
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # We mimic a real browser to avoid basic bot-blockers
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = await client.get(url, headers=headers, timeout=30.0)

            # 4. Check for Authentication Walls
            if response.status_code in [401, 403] or 'login' in str(response.url):
                raise PermissionError(
                    "<b>Authentication Wall Hit!</b>\n"
                    "The NIBM server blocked the bot because it requires your student login. "
                    "The bot cannot bypass this security layer natively."
                )

            if response.status_code != 200:
                raise ValueError(f"Server rejected connection (Error {response.status_code}).")

            # 5. Load into RAM
            file_buffer = io.BytesIO(response.content)
            
            # Extract ID for the filename
            file_id = url.split('id=')[-1] if 'id=' in url else "scraped_file"
            filename = f"NIBM_Module_{file_id}.h5p"

            return file_buffer, filename