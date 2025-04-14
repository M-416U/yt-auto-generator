from flask import render_template, request, redirect, url_for, flash
from app import app
from extensions import db
from models.models import Video
from generate_captions import generate as generate_captions, burn_subtitles_to_video
from video_creator import cleanup_temp_files, create_video_from_images_and_audio
import os


@app.route("/<int:video_id>/create_video", methods=["GET", "POST"])
def create_video(video_id):
    video = Video.query.get_or_404(video_id)

    if not video.script or not video.script.audio_file:
        flash("Audio not generated. Please generate audio first.", "error")
        return redirect(url_for("generate_audio", video_id=video.id))

    if request.method == "POST":
        try:
            create_video_from_images_and_audio(video)
            video.status = "captions_pending"
            db.session.commit()
            flash("Video created successfully!", "success")
            return redirect(url_for("video.add_captions", video_id=video.id))
        except Exception as e:
            flash(f"Error creating video: {str(e)}", "error")
            return redirect(url_for("video.create_video", video_id=video.id))

    return render_template("create_video.html", video=video)


@app.route("/<int:video_id>/add_captions", methods=["GET", "POST"])
def add_captions(video_id):
    video = Video.query.get_or_404(video_id)

    video_path = os.path.join(app.config["OUTPUT_FOLDER"], f"video_{video.id}.mp4")
    if not os.path.exists(video_path):
        flash("Video not found. Please create the video first.", "error")
        return redirect(url_for("video.create_video", video_id=video.id))

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

            # Update video status
            video.status = "completed"
            db.session.commit()

            # Clean up temporary files
            cleanup_temp_files(video, keep_final=True)

            flash("Captions added successfully! Video creation complete.", "success")
            return redirect(url_for("video.view_final_video", video_id=video.id))

        except Exception as e:
            flash(f"Error adding captions: {str(e)}", "error")
            return redirect(url_for("video.add_captions", video_id=video.id))

    return render_template(
        "add_captions.html",
        video=video,
        preview_image=preview_image,
        preview_dimensions=preview_dimensions,
    )


@app.route("/<int:video_id>/view_final")
def view_final_video(video_id):
    video = Video.query.get_or_404(video_id)

    # Check for video with subtitles first
    video_with_subs_path = os.path.join(
        app.config["OUTPUT_FOLDER"], f"video_{video.id}_with_subs.mp4"
    )
    video_path = os.path.join(app.config["OUTPUT_FOLDER"], f"video_{video.id}.mp4")

    # Use the video with subtitles if available, otherwise use the regular video
    if os.path.exists(video_with_subs_path):
        video_url = f"/output/video_{video.id}_with_subs.mp4"
    elif os.path.exists(video_path):
        video_url = f"/output/video_{video.id}.mp4"
    else:
        flash("Video file not found", "error")
        return redirect(url_for("video.view_video", video_id=video_id))

    return render_template("view_final_video.html", video=video, video_url=video_url)
