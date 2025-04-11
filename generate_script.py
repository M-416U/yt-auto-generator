import os
from google import genai
from google.genai import types
import json
import re
from prompts import getStoryGeneratorPrompt, getFactsGeneratorPrompt, getTopXPrompt
from utils import extract_json_from_response

class GeminiVideoScriptGenerator:
    """Class to generate a video script"""

    def __init__(self, api_key=os.getenv("GEMINI_API_KEY")):
        self.client = genai.Client(api_key=api_key)

    def generate_video_script(
        self,
        topic: str,
        video_type: str = "story",
        duration: int = 60,
        style="realistic",
    ) -> dict:
        if video_type == "facts":
            prompt = getFactsGeneratorPrompt(topic, duration=duration)
        elif video_type == "topX":
            prompt = getTopXPrompt(topic, duration=duration)
        else:
            prompt = getStoryGeneratorPrompt(topic, duration=duration)
        try:
            visual_prompt = f"make sure your visual are in this style {style} images"
            print("Prompt: ", prompt)
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt + visual_prompt,
                config=types.GenerateContentConfig(response_modalities=["text"]),
            )

            raw_text = response.candidates[0].content.parts[0].text
            return self.extract_json_from_response(raw_text)
        except Exception as e:
            print("Error generating video script:", str(e), response)
            return None
