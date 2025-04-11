import os
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from utils import use_placeholder_image


class AIImageGenerator:
    """Class for generating images using Google's Gemini API"""

    def __init__(self, api_key=os.getenv("GEMINI_API_KEY")):
        self.client = genai.Client(api_key=api_key)

    def download_image(
        self,
        query,
        output_path,
        target_width=1080,
        target_height=1920,
        image_style="realistic",
    ):
        """
        Generate and save an image based on the query
        """
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
            print(f"Error generating AI image: {e}")
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
