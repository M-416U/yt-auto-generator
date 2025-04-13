import os
from google import genai
from google.genai import types
import json
import re
from prompts import (
    generate_niche_video_prompts,
)
from utils import extract_json_from_response


class GeminiVideoScriptGenerator:
    """Class to generate a video script"""

    def __init__(self, api_key=os.getenv("GEMINI_API_KEY")):
        self.client = genai.Client(api_key=api_key)

    def generate_video_script(
        self,
        video_type: str = "story",
        duration: int = 60,
        style="realistic",
        tone="conversational",
        writing_style="direct",
        niche: str = None,
        main_idea: str = None,
    ) -> dict:

        if not niche or not main_idea:
            raise ValueError("Niche and main_idea are required for niche video types")
        
        prompts = generate_niche_video_prompts(
            niche=niche,
            tone=tone,
            style=writing_style,
            main_idea=main_idea,
            duration=duration,
        )
        prompt = prompts[video_type]

        try:
            visual_prompt = f"make sure your visual are in this style {style} images"
            full_prompt = f"{prompt} {visual_prompt}"
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[{"text": full_prompt}],
                config=types.GenerateContentConfig(response_modalities=["text"]),
            )

            raw_text = response.candidates[0].content.parts[0].text
            return extract_json_from_response(raw_text)
        except Exception as e:
            print("Error generating video script:", str(e))
            return None
