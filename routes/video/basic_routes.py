from flask import render_template, request, redirect, url_for, flash
from app import app
from extensions import db
from models.models import Video, Script
from generate_script import GeminiVideoScriptGenerator
import json
import os
import threading


@app.route("/new", methods=["GET", "POST"])
def new_video():
    if request.method == "POST":
        topic = request.form.get("main_idea")
        video_type = request.form.get("video_type", "story")
        width = int(request.form.get("width", 720))
        height = int(request.form.get("height", 1280))
        duration = int(request.form.get("duration", 60))
        image_style = request.form.get("image_style", "realistic")
        tone = request.form.get("tone", "conversational")
        writing_style = request.form.get("writing_style", "direct")

        # New parameters for niche videos
        niche = request.form.get("niche")
        main_idea = request.form.get("main_idea")

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
            niche=niche,
            main_idea=main_idea,
            status="processing",
        )

        db.session.add(video)
        db.session.commit()

        # Start the background task
        thread = threading.Thread(target=generate_script_task, args=(video.id,))
        thread.daemon = True
        thread.start()

        flash(
            "Video project created! Script generation started in the background.",
            "success",
        )
        return redirect(url_for("index"))

    return render_template("new_video.html")


def generate_script_task(video_id):
    with app.app_context():
        video = Video.query.get(video_id)
        if not video:
            return

        try:
            generator = GeminiVideoScriptGenerator()
            script_data = generator.generate_video_script(
                video_type=video.video_type,
                duration=video.duration,
                style=video.image_style,
                tone=video.tone,
                writing_style=video.writing_style,
                niche=video.niche,
                main_idea=video.main_idea,
            )

            if script_data:
                # Update video with real title and description
                video.title = script_data.get("title", f"Video about {video.topic}")
                video.description = script_data.get("desc", "No description available")

                # Create new script
                script = Script(video_id=video.id, content=json.dumps(script_data))
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


@app.route("/<int:video_id>")
def view_video(video_id):
    video = Video.query.get_or_404(video_id)
    return render_template("view_video.html", video=video)


@app.route("/<int:video_id>/delete", methods=["POST"])
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)

    # Delete associated files
    if video.script and video.script.audio_file:
        try:
            audio_path = os.path.join(
                app.config["OUTPUT_AUDIOS"], os.path.basename(video.script.audio_file)
            )
            if os.path.exists(audio_path):
                os.remove(audio_path)
                video.script.audio_file = None
        except Exception as e:
            print(f"Error removing audio file: {str(e)}")

    for image in video.images:
        if image.file_path:
            try:
                image_path = os.path.join(
                    app.config["OUTPUT_IMAGES"],
                    os.path.basename(image.file_path.replace("output_images/", "")),
                )
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Error removing image file: {str(e)}")

    # Delete video files using stored paths
    if video.video_path:
        try:
            path = os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(video.video_path))
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Error removing video file: {str(e)}")
            
    if video.video_with_subs_path:
        try:
            path = os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(video.video_with_subs_path))
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Error removing video with subs file: {str(e)}")

    db.session.delete(video)
    db.session.commit()

    flash("Video project deleted successfully!", "success")
    return redirect(url_for("index"))
