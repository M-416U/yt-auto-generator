import os
import base64
import requests
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from utils import use_placeholder_image


class AIImageGenerator:
    """Class for generating images using Google's Gemini API or ImageRouter API"""

    def __init__(
        self, api_key=os.getenv("GEMINI_API_KEY"), ir_api_key=os.getenv("IR_API_KEY")
    ):
        self.gemini_api_key = api_key
        self.ir_api_key = ir_api_key
        self.client = genai.Client(api_key=api_key) if api_key else None

    def download_image(
        self,
        query,
        output_path,
        target_width=1080,
        target_height=1920,
        image_style="realistic",
        use_ir=True,
        ir_model="black-forest-labs/FLUX-1-schnell:free",
        ir_quality="medium",
    ):
        """
        Generate and save an image based on the query

        Args:
            query (str): The prompt for image generation
            output_path (str): Path to save the generated image
            target_width (int): Target width for the image
            target_height (int): Target height for the image
            image_style (str): Style of the image (for Gemini API)
            use_ir (bool): Whether to use ImageRouter API instead of Gemini
            ir_model (str): Model to use with ImageRouter API
            ir_quality (str): Quality setting for OpenAI models (low, medium, high)

        Returns:
            bool: True if image generation was successful, False otherwise
        """
        if use_ir:
            return self._generate_with_ir(query, output_path, ir_model, ir_quality)
        else:
            return self._generate_with_gemini(
                query, output_path, target_width, target_height, image_style
            )

    def _generate_with_gemini(
        self,
        query,
        output_path,
        target_width=1080,
        target_height=1920,
        image_style="realistic",
    ):
        """
        Generate and save an image using Gemini API
        """
        if not self.client:
            print("Gemini API key not set")
            return False

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp-image-generation",
                contents=(
                    f"""generate an image with style of {image_style},
                    about ({query}) ,
                    if something not clear you figure it out,
                    if you can't generate the image for any reason,
                    please generate a placeholder image that is close for what i asked instead
                    try to keep the image in the center of the frame with this dimensions:
                    width: {target_width + 300},
                    height: {target_height + 300}
                    """,
                ),
                config=types.GenerateContentConfig(
                    response_modalities=["Text", "Image"]
                ),
            )
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(part.text)
                elif part.inline_data is not None:
                    image = Image.open(BytesIO((part.inline_data.data)))
                    image.save(output_path)
                    return True
            return False

        except Exception as e:
            print(f"Error generating AI image with Gemini: {e}")
            return False

    def _generate_with_ir(
        self, query, output_path, model="stabilityai/sdxl-turbo", quality="medium"
    ):
        """
        Generate and save an image using ImageRouter API

        Args:
            query (str): The prompt for image generation
            output_path (str): Path to save the generated image
            model (str): Model to use with ImageRouter API
            quality (str): Quality setting for OpenAI models (low, medium, high)

        Returns:
            bool: True if image generation was successful, False otherwise
        """
        if not self.ir_api_key:
            print("ImageRouter API key not set")
            return False

        try:
            url = "https://ir-api.myqa.cc/v1/openai/images/generations"
            payload = {"prompt": query, "model": model, "quality": quality}
            headers = {
                "Authorization": f"Bearer {self.ir_api_key}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()

            if "data" not in response_data or not response_data["data"]:
                print(f"Error in ImageRouter API response: {response_data}")
                return False

            # Handle the first image in the response
            image_data = response_data["data"][0]

            # Handle both URL and base64 response formats
            if "url" in image_data and image_data["url"]:
                # Download image from URL
                img_response = requests.get(image_data["url"])
                if img_response.status_code == 200:
                    image = Image.open(BytesIO(img_response.content))
                    image.save(output_path)
                    return True
                else:
                    print(
                        f"Failed to download image from URL: {img_response.status_code}"
                    )
                    return False
            elif "b64_json" in image_data and image_data["b64_json"]:
                # Decode base64 image data
                image_bytes = base64.b64decode(image_data["b64_json"])
                image = Image.open(BytesIO(image_bytes))
                image.save(output_path)
                return True
            else:
                print("No image data found in response")
                return False

        except Exception as e:
            print(f"Error generating AI image with ImageRouter: {e}")
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
