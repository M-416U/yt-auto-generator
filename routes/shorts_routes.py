from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from app import app
from extensions import db
from models.models import YouTubeSource, YouTubeShort
from test import get_transcript, process_transcript_parts
from utils import extract_json_from_response
import json
import os
import subprocess
from threading import Thread
import time
import re


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


@app.route("/shorts/source/<int:source_id>")
def view_shorts_source(source_id):
    source = YouTubeSource.query.get_or_404(source_id)
    shorts = YouTubeShort.query.filter_by(youtube_source_id=source_id).all()

    # Check if processing is complete
    processing_complete = all(short.status != "processing" for short in shorts)

    # Get the first completed short to display by default
    selected_short = None
    for short in shorts:
        if short.status == "completed":
            selected_short = short
            break

    return render_template(
        "view_shorts_source.html",
        source=source,
        shorts=shorts,
        processing_complete=processing_complete,
        selected_short=selected_short,
        selected_short_id=selected_short.id if selected_short else None,
    )


@app.route("/shorts/source/<int:source_id>/short/<int:short_id>")
def view_short_in_source(source_id, short_id):
    source = YouTubeSource.query.get_or_404(source_id)
    shorts = YouTubeShort.query.filter_by(youtube_source_id=source_id).all()
    selected_short = YouTubeShort.query.get_or_404(short_id)

    # Ensure the short belongs to this source
    if selected_short.youtube_source_id != source_id:
        flash("This short does not belong to the selected source", "error")
        return redirect(url_for("view_shorts_source", source_id=source_id))

    # Check if processing is complete
    processing_complete = all(short.status != "processing" for short in shorts)

    return render_template(
        "view_shorts_source.html",
        source=source,
        shorts=shorts,
        processing_complete=processing_complete,
        selected_short=selected_short,
        selected_short_id=short_id,
    )


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

    # Start background processing
    thread = Thread(target=process_generate_shorts, args=(source_id,))
    thread.daemon = True
    thread.start()

    flash("Shorts generation started! This may take several minutes.", "success")
    return redirect(url_for("view_shorts_source", source_id=source_id))


def process_generate_shorts(source_id):
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


@app.route("/shorts/view/<int:short_id>")
def view_short(short_id):
    short = YouTubeShort.query.get_or_404(short_id)
    return render_template("view_short.html", short=short)


@app.route("/shorts/download/<int:short_id>")
def download_short(short_id):
    short = YouTubeShort.query.get_or_404(short_id)

    if not short.output_file:
        flash("Short video file not found", "error")
        return redirect(url_for("view_short", short_id=short.id))

    video_path = os.path.join(app.config["OUTPUT_FOLDER"], short.output_file)

    if not os.path.exists(video_path):
        flash("Short video file not found", "error")
        return redirect(url_for("view_short", short_id=short.id))

    return send_file(video_path, as_attachment=True, download_name=f"{short.title}.mp4")


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


@app.route("/shorts/source/<int:source_id>/delete", methods=["POST"])
def delete_shorts_source(source_id):
    source = YouTubeSource.query.get_or_404(source_id)

    try:
        # Delete all associated shorts first
        shorts = YouTubeShort.query.filter_by(youtube_source_id=source_id).all()

        # Delete video files if they exist
        for short in shorts:
            if short.output_file:
                video_path = os.path.join(
                    app.config["OUTPUT_FOLDER"], short.output_file
                )
                if os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except Exception as e:
                        print(f"Error deleting file {video_path}: {str(e)}")

            db.session.delete(short)

        # Delete the source
        db.session.delete(source)
        db.session.commit()

        flash("YouTube source and all associated shorts have been deleted", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting source: {str(e)}", "error")

    return redirect(url_for("all_shorts_sources"))


@app.route("/shorts/delete/<int:short_id>", methods=["POST"])
def delete_short_from_source(short_id):
    short = YouTubeShort.query.get_or_404(short_id)
    source_id = short.youtube_source_id

    try:
        # Delete video file if it exists
        if short.output_file:
            video_path = os.path.join(app.config["OUTPUT_FOLDER"], short.output_file)
            if os.path.exists(video_path):
                try:
                    os.remove(video_path)
                except Exception as e:
                    print(f"Error deleting file {video_path}: {str(e)}")

        # Delete the short from database
        db.session.delete(short)
        db.session.commit()

        flash("Short has been deleted successfully", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting short: {str(e)}", "error")

    return redirect(url_for("view_shorts_source", source_id=source_id))
