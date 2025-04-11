import os
import requests
import urllib.parse
from bs4 import BeautifulSoup
from PIL import Image
import shutil
from utils import use_placeholder_image


class ImageScraper:
    """Class for scraping images from the web based on search queries"""

    def __init__(self):
        # Set up headers to mimic a browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.min_width = 1080
        self.min_height = 1920

    def search_images(self, query, max_results=5):
        """
        Search for images using the query.
        Tries Bing first, falls back to Google if needed.
        """
        image_urls = []

        try:
            # Try Bing Images first
            bing_url = (
                f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}"
                f"&qft=+filterui:imagesize-custom_1080_1920&form=IRFLTR"
            )
            response = requests.get(bing_url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                for img in soup.find_all("img", class_="mimg"):
                    src = img.get("src")
                    if src and not src.startswith("data:"):
                        image_urls.append(src)

                if image_urls:
                    return image_urls[:max_results]

            # Fallback: Try Google Images
            google_url = (
                "https://www.google.com/search"
                f"?as_q={urllib.parse.quote(query)}"
                f"&as_st=y&imgar=t%7Cxt&udm=2"
            )
            response = requests.get(google_url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                for img in soup.find_all("img"):
                    src = img.get("src")
                    if src and not src.startswith("data:"):
                        if src.startswith("//"):
                            src = "https:" + src
                        image_urls.append(src)

        except Exception as e:
            print(f"Error searching for images: {e}")

        return image_urls[:max_results]

    def download_image(
        self, query, output_path, target_width=1080, target_height=1920, image_style=""
    ):
        """
        Download an image based on the query
        """
        self.min_width = target_width
        self.min_height = target_height
        try:
            image_urls = self.search_images(query)
            for url in image_urls:
                try:
                    response = requests.get(
                        url, headers=self.headers, stream=True, timeout=5
                    )
                    if response.status_code == 200:
                        # Check if content type is an image
                        if not response.headers.get("content-type", "").startswith(
                            "image/"
                        ):
                            print("Skipping: Not an image content type")
                            continue

                        with open(output_path, "wb") as f:
                            response.raw.decode_content = True
                            shutil.copyfileobj(response.raw, f)

                        try:
                            with Image.open(output_path) as img:
                                # if (
                                #     img.width >= self.min_width
                                #     and img.height >= self.min_height
                                # ) or (
                                #     img.width >= self.min_height
                                #     and img.height >= self.min_width
                                # ):
                                return True
                                # else:
                                #     print(f"Image too small: {img.size}")
                        except Exception as e:
                            print(f"Failed to verify image: {e}")
                            if os.path.exists(output_path):
                                os.remove(output_path)
                            continue

                except Exception as e:
                    print(f"Failed to download {url}: {e}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    continue

            return False

        except Exception as e:
            print(f"Error in download process: {e}")
            return False

    def use_placeholder(self, output_path):
        """
        Create a placeholder image when download fails

        Args:
            output_path (str): Path to save the placeholder
        """
        try:
            use_placeholder_image(output_path)
        except Exception as e:
            print(f"Error creating placeholder: {e}")
