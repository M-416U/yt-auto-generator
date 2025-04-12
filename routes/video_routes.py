from flask import (
    render_template,
    request,
    redirect,
    send_file,
    url_for,
    flash,
    send_from_directory,
)
from app import app
from extensions import db
import os
from moviepy.editor import *
from generate_captions import (
    generate as generate_captions,
    burn_subtitles_to_video,
)
from video_creator import cleanup_temp_files, create_video_from_images_and_audio
from models.models import Video, Script
from generate_script import GeminiVideoScriptGenerator
import json


@app.route("/video/new", methods=["GET", "POST"])
def new_video():
    if request.method == "POST":
        topic = request.form.get("topic")
        video_type = request.form.get("video_type", "story")
        width = int(request.form.get("width", 720))
        height = int(request.form.get("height", 1280))
        duration = int(request.form.get("duration", 60))
        image_style = request.form.get("image_style", "realistic")
        tone = request.form.get("tone", "conversational")
        writing_style = request.form.get("writing_style", "direct")

        video = Video(
            title=f"Video about {topic}",
            description="Processing...",
            topic=topic,
            video_type=video_type,
            width=width,
            height=height,
            duration=duration,
            image_style=image_style,
            tone=tone,
            writing_style=writing_style,
            status="processing",
        )

        db.session.add(video)
        db.session.commit()

        from threading import Thread

        def generate_script_task(video_id):
            with app.app_context():
                video = Video.query.get(video_id)
                if not video:
                    return

                try:
                    generator = GeminiVideoScriptGenerator()
                    script_data = generator.generate_video_script(
                        video.topic,
                        video.video_type,
                        duration=video.duration,
                        style=video.image_style,
                        tone=video.tone,
                        writing_style=video.writing_style,
                    )

                    if script_data:
                        # Update video with real title and description
                        video.title = script_data.get(
                            "title", f"Video about {video.topic}"
                        )
                        video.description = script_data.get(
                            "desc", "No description available"
                        )

                        # Create new script
                        script = Script(
                            video_id=video.id, content=json.dumps(script_data)
                        )
                        db.session.add(script)
                        # Update video status
                        video.status = "images_pending"
                    else:
                        video.status = "script_failed"

                    db.session.commit()
                except Exception as e:
                    video.status = "script_failed"
                    db.session.commit()
                    print(f"Error generating script: {str(e)}")

        # Start the background task
        thread = Thread(target=generate_script_task, args=(video.id,))
        thread.daemon = True
        thread.start()

        flash(
            "Video project created! Script generation started in the background.",
            "success",
        )
        return redirect(url_for("index"))

    return render_template("new_video.html")


@app.route("/video/<int:video_id>")
def view_video(video_id):
    video = Video.query.get_or_404(video_id)
    return render_template("view_video.html", video=video)


@app.route("/video/<int:video_id>/delete", methods=["POST"])
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)

    # Delete associated files
    if video.script and video.script.audio_file:
        try:
            os.remove(video.script.audio_file)
        except:
            pass

    for image in video.images:
        if image.file_path:
            try:
                os.remove(image.file_path)
            except:
                pass

    # Delete final video if exists
    final_video_path = os.path.join(
        app.config["OUTPUT_FOLDER"], f"video_{video.id}.mp4"
    )
    final_video_with_subs_path = os.path.join(
        app.config["OUTPUT_FOLDER"], f"video_{video.id}_with_subs.mp4"
    )

    for path in [final_video_path, final_video_with_subs_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    db.session.delete(video)
    db.session.commit()

    flash("Video project deleted successfully!", "success")
    return redirect(url_for("index"))


@app.route("/video/<int:video_id>/create_video", methods=["GET", "POST"])
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
            return redirect(url_for("add_captions", video_id=video.id))
        except Exception as e:
            flash(f"Error creating video: {str(e)}", "error")
            return redirect(url_for("create_video", video_id=video.id))

    return render_template("create_video.html", video=video)


@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(os.path.abspath(app.config["OUTPUT_FOLDER"]), filename)


@app.route("/video/<int:video_id>/add_captions", methods=["GET", "POST"])
def add_captions(video_id):
    video = Video.query.get_or_404(video_id)

    video_path = os.path.join(app.config["OUTPUT_FOLDER"], f"video_{video.id}.mp4")
    if not os.path.exists(video_path):
        flash("Video not found. Please create the video first.", "error")
        return redirect(url_for("create_video", video_id=video.id))

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


@app.route("/video/<int:video_id>/view_final")
def view_final_video(video_id):
    video = Video.query.get_or_404(video_id)

    # Check for video with subtitles first
    video_with_subs_path = os.path.join(
        app.config["OUTPUT_FOLDER"], f"video_{video.id}_with_subs.mp4"
    )
    print(video_with_subs_path)
    video_path = os.path.join(app.config["OUTPUT_FOLDER"], f"video_{video.id}.mp4")
    print(video_path)

    # Use the video with subtitles if available, otherwise use the regular video
    if os.path.exists(video_with_subs_path):
        video_url = f"/output/video_{video.id}_with_subs.mp4"
        print("exist")
    elif os.path.exists(video_path):
        print("not-exist")
        video_url = f"/output/video_{video.id}.mp4"
    else:
        flash("Video file not found", "error")
        return redirect(url_for("view_video", video_id=video_id))

    return render_template("view_final_video.html", video=video, video_url=video_url)


@app.route("/video/<int:video_id>/download")
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
        return redirect(url_for("view_video", video_id=video_id))
