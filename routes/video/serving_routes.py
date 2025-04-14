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

    # Use the paths stored in the database
    if video.video_with_subs_path and os.path.exists(os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(video.video_with_subs_path))):
        video_path = os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(video.video_with_subs_path))
    elif video.video_path and os.path.exists(os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(video.video_path))):
        video_path = os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(video.video_path))
    else:
        flash("Video file not found", "error")
        return redirect(url_for("view_video", video_id=video_id))

    return send_file(
        video_path, as_attachment=True, download_name=f"{video.title}.mp4"
    )
