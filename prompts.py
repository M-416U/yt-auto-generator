def getStoryGeneratorPrompt(story_type="kids", duration: int = 60):
    return f"""
Act like a creative screenwriter and storyteller who specializes in short viral videos.
I want you to write a unique and gripping short story script for a video that fits this style: {story_type}
The story must be highly engaging, emotionally compelling, and keep viewers hooked until the very end. Make it feel like a mini-movie in around {duration} seconds.

Important: The script should contain actual dialog or narration text that will be spoken in the video, not descriptions of scenes.

Return the response in this JSON format exactly, with each script line paired with a short prompt to generate an AI image that matches the scene visually.
{{
 "title": "Insert a short, catchy title that's optimized for virality and SEO",
 "desc": "Short description to be used for the video caption — punchy and engaging",
 "script": [
   "Line 1 of actual spoken dialog or narration",
   ... more lines until it match duration needed
 ],
 "assets": [
  "Detailed visual prompt for image",
  ...
 ]
}}
 - make sure the images order and amount match the script lines.
 - make sure the script lines contain actual spoken text, not scenario descriptions like "(speaker: text)"
"""


def getFactsGeneratorPrompt(topic, duration: int = 60):
    return f"""
I want you to create a {duration}-second YouTube short video script about {topic}. 
The video should be packed with viral potential, and strong hooks to capture viewers immediately and keep them watching until the end.

Important: The script should contain actual spoken narration text that will be read aloud in the video, not descriptions of what happens.

Your response must follow this exact structure:
{{
 "title": "Insert a short, catchy title that's optimized for virality and SEO",
 "desc": "Short description to be used for the video caption — punchy and engaging",
 "script": [
   "Line 1 of actual spoken narration with a fact",
   ... more lines until it match duration needed
 ],
 "assets": [
  "Detailed visual prompt for image",
  ...
 ]
}}
- make sure the images order and amount match the script lines.
- make sure the script lines contain actual spoken text, not scenario descriptions like "(speaker: text)"
- Each line must have a matching image prompt that visually represents the fact.
- Use fun and curious facts that drive watch time.
"""


def getTopXPrompt(topic: str = "tech", count: int = 5, duration: int = 60):
    return f"""
Act like a viral video scriptwriter who specializes in highly engaging short-form Top {count} list videos.
Write a short, punchy script for a **Top {count}** list video based on this topic: **"{topic}"**
Make it informative, fast-paced, and addictive to watch. Include fun or surprising facts, with each item being visually and verbally engaging. End with a satisfying or curious closing line to keep viewers thinking or sharing.

Important: The script should contain actual spoken narration text that will be read aloud in the video, not descriptions of what happens.

Respond in this **exact JSON format**:
{{
 "title": "Insert a short, catchy title that's optimized for virality and SEO",
 "desc": "Short description to be used for the video caption — punchy and engaging",
 "script": [
   "Intro line that hooks the viewer",
   "Number {count}: Actual spoken narration about item {count}",
   "Number {count-1}: Actual spoken narration about item {count-1}",
   "... and so on for each item",
   "Closing line that encourages engagement"
 ],
 "assets": [
  "Detailed visual prompt for intro image",
  "Detailed visual prompt for item {count} image",
  "Detailed visual prompt for item {count-1} image",
  "... and so on for each item",
  "Detailed visual prompt for closing image"
 ]
}}
 - make sure the images order and amount match the script lines.
 - make sure the script lines contain actual spoken text, not scenario descriptions like "(speaker: text)"
- Include exactly {count + 2} script lines (1 intro + {count} list items + 1 closing).
- Each line must have a matching image prompt that visually represents that item.
- Total video length should be approximately {duration} seconds.
"""


# """
# Write a short,
# first-person monologue script for a voiceover video. The tone is [{tone}],
# the writing style should be [{style}],
# and the main idea is [{main_idea}].
# Keep it emotionally engaging, concise, and impactful.
# Estimated length: [{duration}] seconds.
# Focus on grabbing attention fast,
# delivering a strong message, and ending with a memorable closing line.
# """


def getMonologuePrompt(
    topic: str, duration: int = 60, tone: str = "conversational", style: str = "direct"
):
    return f"""
Act like a professional voiceover scriptwriter who specializes in impactful first-person monologues.
Write a short, first-person monologue script about this topic: {topic}
The tone should be {tone}, and the writing style should be {style}.
Make it emotionally engaging, concise, and impactful. Keep it around {duration} seconds.

Important: The script should contain actual spoken narration text that will be read aloud in the video, not descriptions of what happens.

Return the response in this JSON format exactly:
{{
 "title": "Insert a short, catchy title that's optimized for virality and SEO",
 "desc": "Short description to be used for the video caption — punchy and engaging",
 "script": [
   "Line 1 of actual spoken monologue",
   ... more lines until it match duration needed
 ],
 "assets": [
  "Detailed visual prompt for image",
  ...
 ]
}}
- make sure the images order and amount match the script lines.
- make sure the script lines contain actual spoken text, not scenario descriptions.
- Focus on grabbing attention fast and ending with a memorable closing line.
"""


def generate_niche_video_prompts(
    niche: str, tone: str, style: str, main_idea: str, duration: int
):
    response_format = """
    Return the response in this JSON format exactly:" + response_format
    {
      "title": "Insert a short, catchy title that's optimized for virality and SEO",
      "desc": "description to be used for the video caption — punchy and engaging",
      "script": [
        "Line 1 of actual spoken monologue",
        ... more lines until it match duration needed
      ],
      "assets": [
        "Detailed visual prompt for image",
        ...
      ]
    }
  """
    niche_context = {
        "fitness": "The script should appeal to people who want to transform their bodies and mindset through discipline and physical effort.",
        "finance": "Speak to individuals who are trying to build wealth, escape debt, or gain financial freedom.",
        "relationships": "Address emotional intelligence, connection, heartbreak, or personal growth in love and friendship.",
        "mindset": "Encourage mental resilience, personal growth, self-awareness, and discipline.",
        "business": "Speak to ambitious entrepreneurs, creators, or professionals seeking success, impact, or independence.",
        "health": "Focus on holistic well-being, habits, self-care, and the pursuit of a healthier life.",
        "self-worth": "Inspire people to recognize their value, reclaim confidence, and overcome self-doubt.",
    }

    context = niche_context.get(
        niche.lower(),
        "Make the message universally relatable and emotionally compelling.",
    )

    prompts = {}

    prompts["social_video"] = (
        f"Write a short, first-person monologue script for a voiceover video. "
        f"The tone is {tone}, the writing style is {style}, and the main idea is: {main_idea}. "
        f"Estimated duration: {duration} seconds. {context} "
        f"Start with a strong hook, build tension or clarity in the body, and end with a bold, memorable conclusion.",
        response_format,
    )

    prompts["generative_ai"] = (
        f"Create a 4-second visual AI video that reflects this concept: {main_idea}. "
        f"Make the visuals align with a {tone} tone and a {style} aesthetic. "
        f"Target audience: people interested in {niche}. Include emotional impact through color, motion, or metaphor.",
        response_format,
    )

    prompts["clip_summary"] = (
        f"Summarize a long-form video into a short-form social clip (under {duration} seconds spoken). "
        f"Topic: {main_idea}. Style: {style}. Tone: {tone}. "
        f"Niche: {niche}. Hook viewers immediately with a scroll-stopping line, and deliver a quick punch of insight or emotion.",
        response_format,
    )

    return prompts
