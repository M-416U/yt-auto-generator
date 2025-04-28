from flask import redirect, url_for, flash, jsonify, request
from app import app
from extensions import db
from models.models import YouTubeSource, YouTubeShort
import os
import subprocess
from threading import Thread
import time
import re
from generate_captions import generate as generate_captions, burn_subtitles_to_video


@app.route("/shorts/toggle/<int:short_id>", methods=["POST"])
def toggle_short_selection(short_id):
    short = YouTubeShort.query.get_or_404(short_id)
    if short.status == "completed":
        return jsonify({"success": False, "message": "Cannot modify completed shorts"})
    short.selected = not short.selected
    db.session.commit()
    return jsonify({"success": True, "selected": short.selected})


@app.route("/shorts/source/<int:source_id>/generate", methods=["POST"])
def generate_shorts(source_id):
    source = YouTubeSource.query.get_or_404(source_id)
    selected_shorts = YouTubeShort.query.filter_by(
        youtube_source_id=source_id, selected=True
    ).all()

    if not selected_shorts:
        flash("Please select at least one short to generate", "error")
        return redirect(url_for("view_shorts_source", source_id=source_id))

    # Get caption settings from form
    caption_settings = {
        'add_captions': request.form.get('add_captions') == 'on',
        'max_words': int(request.form.get('max_words', 1)),
        'font_size': int(request.form.get('font_size', 40)),
        'position': request.form.get('position', 'bottom'),
        'enable_highlight': request.form.get('enable_highlight') == 'on',
        'highlight_type': request.form.get('highlight_type', ''),
        'highlight_color': request.form.get('highlight_color', ''),
        'custom_highlight_color': request.form.get('custom_highlight_color', '')
    }

    # Start background processing
    thread = Thread(target=process_generate_shorts, args=(source_id, caption_settings))
    thread.daemon = True
    thread.start()

    flash("Shorts generation started! This may take several minutes.", "success")
    return redirect(url_for("view_shorts_source", source_id=source_id))


def process_generate_shorts(source_id, caption_settings=None):
    with app.app_context():
        source = YouTubeSource.query.get(source_id)
        if not source:
            return

        selected_shorts = YouTubeShort.query.filter_by(
            youtube_source_id=source_id, selected=True
        ).all()

        video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", source.url)
        if not video_id:
            return

        video_id = video_id.group(1)

        for short in selected_shorts:
            try:
                short.status = "processing"
                db.session.commit()

                # Create output filename
                output_file = os.path.join(
                    app.config["OUTPUT_FOLDER"], f"short_{short.id}_{video_id}.mp4"
                )

                # Use yt-dlp to download the segment
                start_time = short.start_time
                duration = short.end_time - short.start_time

                command = [
                    "yt-dlp",
                    "-f",
                    "best[height<=1080]",
                    "--external-downloader",
                    "ffmpeg",
                    "--external-downloader-args",
                    f"ffmpeg_i:-ss {start_time} -t {duration}",
                    "-o",
                    output_file,
                    f"https://www.youtube.com/watch?v={video_id}",
                ]

                result = subprocess.run(command, capture_output=True, text=True)

                if os.path.exists(output_file):
                    # Process captions if requested
                    if caption_settings and caption_settings.get('add_captions'):
                        try:
                            # Determine highlight color
                            highlight_color = None
                            if caption_settings.get('enable_highlight'):
                                highlight_type = caption_settings.get('highlight_type')
                                if highlight_type == 'custom':
                                    highlight_color = caption_settings.get('custom_highlight_color')
                                else:
                                    highlight_color = caption_settings.get('highlight_color')
                            
                            # Generate captions
                            srt_path = os.path.join(
                                app.config["OUTPUT_FOLDER"], f"short_{short.id}.srt"
                            )
                            generate_captions(
                                media_file=output_file,
                                max_words_per_caption=caption_settings.get('max_words', 1),
                                highlight_color=highlight_color,
                                caption_format="srt",
                                output_filename=srt_path,
                            )

                            # Burn captions into video
                            output_with_captions = os.path.join(
                                app.config["OUTPUT_FOLDER"], f"short_{short.id}_{video_id}_with_subs.mp4"
                            )
                            burn_subtitles_to_video(
                                video_path=output_file,
                                srt_path=srt_path,
                                output_path=output_with_captions,
                                font_size=caption_settings.get('font_size', 40),
                                position=caption_settings.get('position', 'bottom'),
                            )
                            
                            # If caption generation was successful, use the new file
                            if os.path.exists(output_with_captions):
                                # Remove the original file to save space
                                try:
                                    os.remove(output_file)
                                except Exception as e:
                                    print(f"Error removing original file: {str(e)}")
                                
                                # Update the output file path
                                short.output_file = os.path.basename(output_with_captions)
                            else:
                                # If caption generation failed, keep the original file
                                short.output_file = os.path.basename(output_file)
                        except Exception as e:
                            print(f"Error adding captions to short {short.id}: {str(e)}")
                            # If caption generation fails, still keep the original video
                            short.output_file = os.path.basename(output_file)
                    else:
                        # No captions requested, use the original file
                        short.output_file = os.path.basename(output_file)
                    
                    short.status = "completed"
                else:
                    short.status = "failed"
                    print(f"Failed to generate short: {result.stderr}")

                db.session.commit()
                time.sleep(1)  # Prevent rate limiting

            except Exception as e:
                print(f"Error generating short {short.id}: {str(e)}")
                short.status = "failed"
                db.session.commit()


@app.route("/shorts/source/<int:source_id>/progress")
def shorts_progress(source_id):
    source = YouTubeSource.query.get_or_404(source_id)
    selected_shorts = YouTubeShort.query.filter_by(
        youtube_source_id=source_id, selected=True
    ).all()

    total = len(selected_shorts)
    completed = len([s for s in selected_shorts if s.status == "completed"])
    processing = len([s for s in selected_shorts if s.status == "processing"])
    failed = len([s for s in selected_shorts if s.status == "failed"])

    # Check if any shorts are still processing
    any_processing = (
        YouTubeShort.query.filter_by(
            youtube_source_id=source_id, status="processing"
        ).first()
        is not None
    )

    progress = 0
    if total > 0:
        progress = int((completed / total) * 100)

    return jsonify(
        {
            "total": total,
            "completed": completed,
            "processing": processing,
            "failed": failed,
            "progress": progress,
            "is_complete": not any_processing,
        }
    )