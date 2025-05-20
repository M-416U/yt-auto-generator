import json
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from langdetect import detect
from utils import extract_json_from_response


def get_video_id(video_url):
    # Extract the video ID from the YouTube URL
    video_id = video_url.split("v=")[-1]
    if "&" in video_id:
        video_id = video_id.split("&")[0]
    return video_id


def get_transcript(video_url):
    video_id = get_video_id(video_url)
    print(f"Fetching transcript for video ID: {video_id}")

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id=video_id)

        transcript = None

        for t in transcript_list:
            if t.is_generated:
                transcript = t.fetch()
                break

        if not transcript:
            print("No auto-generated transcript found.")
            return None, None

        full_transcript = ""
        print(transcript[0])
        print(transcript[-1])
        for snippet in transcript:
            full_transcript += (
                f"start:{snippet.start} duration:{snippet.duration} "
                + snippet.text
                + "\n"
            )

        lang = detect(full_transcript)
        print(f"Detected language: {lang}")

        return full_transcript, lang

    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None, None


def split_transcript_into_parts(transcript, max_chars=5000):
    words = transcript.split()
    parts = []
    current_part = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 > max_chars:
            parts.append(" ".join(current_part))
            current_part = [word]
            current_length = len(word)
        else:
            current_part.append(word)
            current_length += len(word) + 1

    if current_part:
        parts.append(" ".join(current_part))
    return parts


genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-lite",
    generation_config=generation_config,
)


def process_transcript_parts(transcript, num_parts=10, max_chars=6000):
    parts = split_transcript_into_parts(transcript, max_chars=max_chars)
    print(f"\nAnalyzing {len(parts)} parts for viral potential:")
    history = []
    for i, part in enumerate(parts, 1):
        history.append(
            {"role": "user", "parts": [{"text": f"Part {i}/{len(parts)}: {part}"}]}
        )
        history.append(
            {
                "role": "model",
                "parts": [{"text": f"Received part {i}"}],
            }
        )

    chat_session = model.start_chat(history=history)

    viral_prompt = f"""
    Based on all the transcript parts, identify the {num_parts} most engaging segments that would make great viral short-form videos (45-59 seconds each).
    For each segment, provide:
    1. A catchy title that would work well on social media
    2. The exact content to include
    3. Why this segment would be engaging
    4. Estimated duration in seconds
    5. Key hashtags to use

    note:
        use the same lang for the generated viral_segments.
        start:the start time in second,
        duration:the duration of the sentance,

    Return as JSON with format:
    {{
        "viral_segments": [
            {{
                "title": "...", // title will be used when publishing on social media use the lang in the transcript
                "desc": "...", // description will be used when publishing on social media use the lang in the transcript
                "viral_potential": "...", // small description why this part might go viral use the lang in the transcript
                "duration_seconds": X,
                "hashtags": [...], use the lang in the transcript
                "hook": "...", // attention-grabbing first 5 seconds
                "score":"number out of 100 for how viral it is",
                "timestamp":{{"start":'5',"end":'61'}}, // in this format the start the first start of the first sentance and end the last end of the last sentance
                "transcript":"the text in the part"
            }}
        ],
        "overall_theme": "...",
        "target_audience": "..."
    }}

    Important: Each segment must be self-contained and impactful within 45-59 seconds.
    Focus on moments that are: surprising, emotional, educational, or highly engaging.
    notes:
        if the part u see is long than 59 seconds then split it into multiple parts 
            ex:
                if the parts is 2.4 minuets
                part 1: 59 seconds
                part 2: 59 seconds
                part 3: 42 seconds
    """

    try:
        response = chat_session.send_message(viral_prompt)
        return response.text

    except Exception as e:
        print(f"Error processing viral segments: {str(e)}")
        return None


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=id"
    transcript, language = get_transcript(video_url)
    if transcript:
        print("Transcript retrieved successfully")
        summaries = process_transcript_parts(transcript)
        print("\nSummaries:")
        print(summaries)
        # Save summaries to a file
        summaries = extract_json_from_response(summaries)
        with open("transcript_summaries.json", "w", encoding="utf-8") as f:
            json.dump(summaries, f, indent=2, ensure_ascii=False)
        print("\nSummaries saved to transcript_summaries.json")
    else:
        print("Failed to retrieve transcript")
