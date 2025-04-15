from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app
from extensions import db
from models.models import Video
from generate_captions import generate as generate_captions, burn_subtitles_to_video
from video_creator import (
    cleanup_temp_files,
    start_video_creation_background,
    get_relative_video_path,
)
import os
from datetime import datetime


@app.route("/<int:video_id>/create_video", methods=["GET", "POST"])
def create_video(video_id):
    video = Video.query.get_or_404(video_id)

    if not video.script or not video.script.audio_file:
        flash("Audio not generated. Please generate audio first.", "error")
        return redirect(url_for("generate_audio", video_id=video.id))

    if request.method == "POST":
        try:
            # Reset any previous error message
            video.error_message = None
            video.progress = 0
            video.last_updated = datetime.utcnow()
            db.session.commit()

            # Start video creation in background
            start_video_creation_background(video)

            flash(
                "Video creation started in the background. You'll be notified when it's ready.",
                "success",
            )
            return redirect(url_for("video_status", video_id=video.id))
        except Exception as e:
            flash(f"Error starting video creation: {str(e)}", "error")
            return redirect(url_for("create_video", video_id=video.id))

    return render_template("create_video.html", video=video)


@app.route("/<int:video_id>/video_status", methods=["GET"])
def video_status(video_id):
    video = Video.query.get_or_404(video_id)
    return render_template("video_status.html", video=video)


@app.route("/<int:video_id>/check_video_status", methods=["GET"])
def check_video_status(video_id):
    video = Video.query.get_or_404(video_id)

    status = video.status
    message = ""
    redirect_url = ""

    if status == "captions_pending":
        message = "Video created successfully!"
        redirect_url = url_for("add_captions", video_id=video.id)
    elif status == "error":
        message = f"Error creating video: {video.error_message or 'Unknown error'}"
    elif status == "processing":
        message = f"Processing video... ({video.progress}% complete)"

    return jsonify(
        {
            "status": status,
            "progress": video.progress,
            "message": message,
            "redirect_url": redirect_url,
            "last_updated": (
                video.last_updated.strftime("%Y-%m-%d %H:%M:%S")
                if video.last_updated
                else None
            ),
        }
    )


@app.route("/<int:video_id>/add_captions", methods=["GET", "POST"])
def add_captions(video_id):
    video = Video.query.get_or_404(video_id)

    # Check if video exists using the path stored in the database
    if not video.video_path or not os.path.exists(
        os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(video.video_path))
    ):
        flash("Video not found. Please create the video first.", "error")
        return redirect(url_for("create_video", video_id=video.id))

    video_path = os.path.join(
        app.config["OUTPUT_FOLDER"], os.path.basename(video.video_path)
    )

    # Get video dimensions for preview
    preview_image = url_for("static", filename=f"image_styles/{video.image_style}.jpeg")
    preview_dimensions = {"width": video.width, "height": video.height}

    if request.method == "POST":
        try:
            # Get caption settings from form
            max_words = int(request.form.get("max_words", 1))
            font_size = int(request.form.get("font_size", 40))
            position = request.form.get("position", "bottom")

            # Handle highlight settings
            enable_highlight = request.form.get("enable_highlight") == "on"
            highlight_color = None

            if enable_highlight:
                highlight_type = request.form.get("highlight_type")
                if highlight_type == "custom":
                    highlight_color = request.form.get("custom_highlight_color")
                else:
                    highlight_color = request.form.get("highlight_color")

            # Generate captions
            srt_path = os.path.join(
                app.config["OUTPUT_FOLDER"], f"video_{video.id}.srt"
            )
            generate_captions(
                media_file=video_path,
                max_words_per_caption=max_words,
                highlight_color=highlight_color,
                caption_format="srt",
                output_filename=srt_path,
            )

            # Burn captions into video
            output_video_path = os.path.join(
                app.config["OUTPUT_FOLDER"], f"video_{video.id}_with_subs.mp4"
            )
            burn_subtitles_to_video(
                video_path=video_path,
                srt_path=srt_path,
                output_path=output_video_path,
                font_size=font_size,
                position=position,
            )

            # Update video status and path in database
            video.status = "completed"
            video.video_with_subs_path = get_relative_video_path(
                video.id, with_subs=True
            )
            db.session.commit()

            # Clean up temporary files
            cleanup_temp_files(video, keep_final=True)

            flash("Captions added successfully! Video creation complete.", "success")
            return redirect(url_for("view_final_video", video_id=video.id))

        except Exception as e:
            flash(f"Error adding captions: {str(e)}", "error")
            return redirect(url_for("add_captions", video_id=video.id))

    return render_template(
        "add_captions.html",
        video=video,
        preview_image=preview_image,
        preview_dimensions=preview_dimensions,
    )


@app.route("/<int:video_id>/view_final")
def view_final_video(video_id):
    video = Video.query.get_or_404(video_id)

    # Use the paths stored in the database
    if video.video_with_subs_path and os.path.exists(
        os.path.join(
            app.config["OUTPUT_FOLDER"], os.path.basename(video.video_with_subs_path)
        )
    ):
        video_url = f"/output/{os.path.basename(video.video_with_subs_path)}"
    elif video.video_path and os.path.exists(
        os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(video.video_path))
    ):
        video_url = f"/output/{os.path.basename(video.video_path)}"
    else:
        flash("Video file not found", "error")
        return redirect(url_for("view_video", video_id=video_id))

    return render_template("view_final_video.html", video=video, video_url=video_url)
