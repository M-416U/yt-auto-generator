from flask import render_template, redirect, url_for, flash
from app import app
from extensions import db
from models.models import Video, YouTubeShort
from models.youtube_account import YouTubeAccount
import os


# Route to show upload form for a video
@app.route("/video/upload/<int:video_id>")
def video_upload_form(video_id):
    video = Video.query.get_or_404(video_id)
    accounts = YouTubeAccount.query.all()

    # Check if video file exists
    video_file_path = os.path.join(
        app.config["OUTPUT_FOLDER"], f"video_{video.id}_with_subs.mp4"
    )
    if not os.path.exists(video_file_path):
        flash("Video file not found. Please generate the video first.", "error")
        return redirect(url_for("index"))

    return render_template(
        "upload/video_upload.html",
        content=video,
        accounts=accounts,
        is_short=False,
        content_type="video",
    )


# Route to show upload form for a short
@app.route("/short/upload/<int:short_id>")
def short_upload_form(short_id):
    short = YouTubeShort.query.get_or_404(short_id)
    accounts = YouTubeAccount.query.all()
    # Check if short file exists
    if not short.output_file or not os.path.exists(
        os.path.abspath(app.config["OUTPUT_FOLDER"]) + "/" + short.output_file
    ):
        flash("Short video file not found. Please generate the short first.", "error")
        return redirect(url_for("all_shorts_sources"))

    return render_template(
        "upload/video_upload.html",
        content=short,
        accounts=accounts,
        is_short=True,
        content_type="short",
    )