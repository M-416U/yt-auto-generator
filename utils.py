import json
import re
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import List, Optional
import random


def use_placeholder_image(output_path):
    """
    Create a placeholder image when download fails

    Args:
        output_path (str): Path to save the placeholder
    """
    try:
        # Create a colored placeholder with text
        width, height = 1080, 1080
        colors = [(255, 105, 180), (100, 149, 237), (50, 205, 50), (255, 165, 0)]

        img = Image.new("RGB", (width, height), random.choice(colors))
        draw = ImageDraw.Draw(img)

        # Add text
        try:
            # Try to load a font, use default if not available
            font = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default()

        text = "Axolotl Image Placeholder"
        text_width = draw.textlength(text, font=font)
        text_position = ((width - text_width) // 2, height // 2)

        draw.text(text_position, text, fill="white", font=font)
        img.save(output_path)
    except Exception as e:
        print(f"Error creating placeholder: {e}")


def find_system_font() -> str:
    """Find available system font."""
    fonts_to_try = [
        "C:\\Windows\\Fonts\\arialbd.ttf",  # Windows
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/Library/Fonts/Arial Bold.ttf",  # macOS
        "arial.ttf",  # Fallback
    ]

    for font in fonts_to_try:
        if Path(font).exists():
            return font
    return "arial.ttf"


def resize_and_crop_image(image: Image.Image, width: int, height: int) -> Image.Image:
    """Resize and crop image to fit target dimensions while maintaining aspect ratio."""
    img_ratio = image.width / image.height
    target_ratio = width / height

    # Make the image larger than target size to allow room for zooming
    # This helps prevent black edges during zoom animations
    scale_factor = 1.5  # Ensure we have enough padding for zooming

    if img_ratio > target_ratio:
        new_height = height
        new_width = int(height * img_ratio)
        image = image.resize((new_width, new_height), Image.LANCZOS)
        left = (new_width - width) // 2
        image = image.crop((left, 0, left + width, height))
    else:  # Image is taller
        new_width = width
        new_height = int(width / img_ratio)
        image = image.resize((new_width, new_height), Image.LANCZOS)
        top = (new_height - height) // 2
        image = image.crop((0, top, width, top + height))

    return image


def extract_json_from_response(text: str) -> dict:
    """
    Tries to cleanly extract JSON from a Text, even if it's embedded in markdown or has extra explanation.
    """
    try:
        # Attempt to extract JSON inside triple backticks ```json ... ```
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Fallback: Try to extract the first full JSON object in the text
        json_start = text.find("{")
        json_end = text.rfind("}")
        if json_start != -1 and json_end != -1:
            cleaned_json = text[json_start : json_end + 1]
            return json.loads(cleaned_json)
    except Exception as e:
        print("Error parsing JSON:", str(e))

    return None
