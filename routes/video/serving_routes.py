from flask import send_from_directory, send_file, flash, redirect, url_for
from app import app
from models.models import Video
import os


@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(os.path.abspath(app.config["OUTPUT_FOLDER"]), filename)


@app.route("/<int:video_id>/download")
def download_video(video_id):
    video = Video.query.get_or_404(video_id)

    # Check for video with subtitles first
    video_with_subs_path = os.path.join(
        app.config["OUTPUT_FOLDER"], f"video_{video.id}_with_subs.mp4"
    )
    video_path = os.path.join(app.config["OUTPUT_FOLDER"], f"video_{video.id}.mp4")

    # Use the video with subtitles if available, otherwise use the regular video
    if os.path.exists(video_with_subs_path):
        return send_file(
            video_with_subs_path, as_attachment=True, download_name=f"{video.title}.mp4"
        )
    elif os.path.exists(video_path):
        return send_file(
            video_path, as_attachment=True, download_name=f"{video.title}.mp4"
        )
    else:
        flash("Video file not found", "error")
        return redirect(url_for("video.view_video", video_id=video_id))
