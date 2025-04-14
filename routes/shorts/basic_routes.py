from flask import render_template, request, redirect, url_for, flash
from app import app
from extensions import db
from models.models import YouTubeSource, YouTubeShort
from summaries_yt import get_transcript, process_transcript_parts
from utils import extract_json_from_response
import json
import os
import re
from threading import Thread


@app.route("/shorts/new", methods=["GET", "POST"])
def new_shorts():
    if request.method == "POST":
        video_url = request.form.get("video_url")
        num_parts = int(request.form.get("num_parts", 5))

        # Check if we already have this YouTube video
        existing_source = YouTubeSource.query.filter_by(url=video_url).first()

        if existing_source:
            return redirect(url_for("view_shorts_source", source_id=existing_source.id))

        # Get transcript and analyze
        transcript, language = get_transcript(video_url)

        if not transcript:
            flash("Failed to retrieve transcript for this video", "error")
            return redirect(url_for("new_shorts"))

        # Create new YouTube source
        source = YouTubeSource(url=video_url, transcript=transcript, language=language)

        db.session.add(source)
        db.session.commit()

        # Start background processing
        thread = Thread(target=process_shorts_segments, args=(source.id, num_parts))
        thread.daemon = True
        thread.start()

        flash("Video analysis started! This may take a few minutes.", "success")
        return redirect(url_for("view_shorts_source", source_id=source.id))

    return render_template("new_shorts.html")


def process_shorts_segments(source_id, num_parts):
    with app.app_context():
        source = YouTubeSource.query.get(source_id)
        if not source:
            return

        try:
            # Process transcript to get viral segments
            response = process_transcript_parts(source.transcript, num_parts=num_parts)
            data = extract_json_from_response(response)

            if not data or "viral_segments" not in data:
                return

            # Update source with title if available
            if "overall_theme" in data:
                source.title = data["overall_theme"]

            # Create short entries for each segment
            for segment in data["viral_segments"]:
                # Parse timestamp
                timestamp = segment.get("timestamp", {})
                start_time = float(timestamp.get("start", 0))
                end_time = float(timestamp.get("end", 60))

                short = YouTubeShort(
                    youtube_source_id=source.id,
                    title=segment.get("title", "Untitled Short"),
                    description=segment.get("desc", ""),
                    viral_potential=segment.get("viral_potential", ""),
                    duration_seconds=segment.get("duration_seconds", 0),
                    hashtags=json.dumps(segment.get("hashtags", [])),
                    hook=segment.get("hook", ""),
                    viral_score=int(segment.get("score", 0)),
                    start_time=start_time,
                    end_time=end_time,
                    transcript=segment.get("transcript", ""),
                )
                db.session.add(short)

            db.session.commit()
        except Exception as e:
            print(f"Error processing shorts segments: {str(e)}")


@app.route("/shorts/all")
def all_shorts_sources():
    """View all YouTube source videos that have been processed for shorts"""
    sources = YouTubeSource.query.order_by(YouTubeSource.created_at.desc()).all()

    # Get count of shorts for each source
    for source in sources:
        source.shorts_count = YouTubeShort.query.filter_by(
            youtube_source_id=source.id
        ).count()
        source.selected_count = YouTubeShort.query.filter_by(
            youtube_source_id=source.id, selected=True
        ).count()
        source.completed_count = YouTubeShort.query.filter_by(
            youtube_source_id=source.id, status="completed"
        ).count()

        # Extract video ID from URL
        video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", source.url)
        if video_id_match:
            source.video_id = video_id_match.group(1)
            source.thumbnail_url = (
                f"https://img.youtube.com/vi/{source.video_id}/mqdefault.jpg"
            )
        else:
            source.thumbnail_url = None

    return render_template("all_shorts_sources.html", sources=sources)