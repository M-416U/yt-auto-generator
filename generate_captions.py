import mimetypes
from pathlib import Path
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
)
import pysrt
import os
import re

import moviepy.config as cfg

cfg.change_settings({"IMAGEMAGICK_BINARY": "magick"})


def generate(
    media_file,
    max_words_per_caption: int = 1,
    highlight_color: str = None,
    caption_format: str = "srt",
    output_filename: str = None,
):
    try:
        import stable_whisper
    except ImportError:
        print("Dependencies to run Whisper locally are not installed,")
        raise

    media_path = Path(media_file)
    mime_type, _ = mimetypes.guess_type(str(media_path))
    is_video = mime_type is not None and mime_type.startswith("video")

    # If mimetypes didn't work, fall back to extension check
    if mime_type is None:
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"]
        is_video = media_path.suffix.lower() in video_extensions

    if not output_filename:
        output_filename = f"{media_path.stem}_captioned.mp4"
        # Extract audio for transcription
    audio_file = f"{media_path.stem}_audio.wav"

    try:
        if is_video:
            # Use MoviePy to extract audio
            video_clip = VideoFileClip(str(media_path))
            video_clip.audio.write_audiofile(str(audio_file), codec="pcm_s16le")
            video_clip.close()
        else:
            # If it's already an audio file, create a copy or convert it to WAV
            audio_clip = AudioFileClip(str(media_path))
            audio_clip.write_audiofile(str(audio_file), codec="pcm_s16le")
            audio_clip.close()
    except Exception as e:
        print(f"Error processing media file: {e}")
        raise

    model = stable_whisper.load_model("base")
    result = model.transcribe(
        str(audio_file),
    )
    if max_words_per_caption and max_words_per_caption > 0:
        result = result.split_by_length(max_words=max_words_per_caption)
    
    # Handle highlighting
    highlight_words = False
    color_tag = None
    if highlight_color:
        highlight_words = True
        color = highlight_color
        if color == "bold":
            color_tag = ("<b>", "</b>")
        else:
            color_tag = (f'<span foreground="{color}">', "</span>")

    result.to_srt_vtt(
        str(output_filename),
        word_level=highlight_words,
        tag=color_tag,
        vtt=caption_format == "vtt",
    )


def burn_subtitles_to_video(
    video_path,
    srt_path,
    output_path=None,
    font_size=24,
    default_color="white",
    position="bottom",
):
    if output_path is None:
        filename, ext = os.path.splitext(video_path)
        output_path = f"{filename}_subbed{ext}"

    video = VideoFileClip(video_path)
    subs = pysrt.open(srt_path)
    subtitle_clips = []

    def parse_spans(text, default_color="white"):
        segments = []
        pattern = r'<span foreground="([^"]+)">(.*?)</span>'
        last_index = 0

        for match in re.finditer(pattern, text):
            color, word = match.groups()
            start, end = match.span()

            if start > last_index:
                before_text = text[last_index:start]
                segments.append((before_text, default_color))

            segments.append((word, color))
            last_index = end

        if last_index < len(text):
            remaining = text[last_index:]
            segments.append((remaining, default_color))

        return segments

    def get_ypos(video_height, text_height, position):
        margin = 20
        if position == "top":
            return margin
        elif position == "middle":
            return (video_height - text_height) // 2
        else:  # default to bottom
            return video_height - text_height - margin

    for sub in subs:
        start_time = sub.start.ordinal / 1000
        end_time = sub.end.ordinal / 1000
        duration = end_time - start_time

        segments = parse_spans(sub.text, default_color)
        text_clips = []

        total_width = 0
        max_height = 0

        for text, color in segments:
            clip = TextClip(
                text,
                fontsize=font_size,
                color=color,
                font="Arial-Bold",
                stroke_width=0,
                bg_color="#00000090",
            )
            total_width += clip.w
            max_height = max(max_height, clip.h)
            text_clips.append(clip)

        xpos = (video.w - total_width) // 2
        ypos = get_ypos(video.h, max_height, position)

        positioned_clips = []
        for clip in text_clips:
            clip = (
                clip.set_position((xpos, ypos))
                .set_start(start_time)
                .set_duration(duration)
            )
            positioned_clips.append(clip)
            xpos += clip.w

        subtitle_clips.extend(positioned_clips)

    final_video = CompositeVideoClip([video] + subtitle_clips)
    final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

    final_video.close()
    video.close()

    return output_path


if __name__ == "__main__":
    generate(
        media_file="./final_video.mp4",
        max_words_per_caption=1,
        highlight_color="yellow",
        caption_format="srt",
        output_filename="output.srt",
    )
    burn_subtitles_to_video(
        video_path="./final_video.mp4",
        srt_path="output.srt",
        output_path="final_video_with_subs.mp4",
        font_size=40,
        position="middle",
    )
