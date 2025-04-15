from flask import render_template, request, redirect, url_for, flash
from app import app
from extensions import db
from models.models import Video
from generate_audio import text_to_speech
import json
import os


@app.route("/video/<int:video_id>/generate_audio", methods=["GET", "POST"])
def generate_audio(video_id):
    video = Video.query.get_or_404(video_id)

    if not video.script:
        flash("No script found. Please generate a script first.", "error")
        return redirect(url_for("generate_script", video_id=video.id))

    # Load speaker data
    with open("vits_speaker_id.json", "r") as f:
        speakers = json.load(f)

    script_data = json.loads(video.script.content)

    if request.method == "POST":
        # Delete existing audio if it exists
        if video.script.audio_file:
            full_path = os.path.join(
                app.config["OUTPUT_AUDIOS"],
                os.path.basename(video.script.audio_file.replace("output_audio/", "")),
            )
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass

        script_text = " ".join(script_data.get("script", []))

        try:
            # Get selected speaker from form
            selected_speaker = request.form.get(
                "speaker", "p228"
            )  # Default to p228 if not specified
            audio_file, total_duration = text_to_speech(
                script_text,
                output_dir=app.config["OUTPUT_AUDIOS"],
                speaker=selected_speaker,
            )

            if not audio_file:
                flash("Failed to generate audio. Please try again.", "error")
                return redirect(url_for("generate_audio", video_id=video.id))

            # Store relative path in database
            filename = os.path.basename(audio_file)
            video.script.audio_file = f"{filename}"
            video.script.audio_duration = total_duration

            # Calculate duration for each image
            num_images = len(video.images)
            if num_images > 0 and total_duration > 0:
                duration_per_image = total_duration / num_images
                for image in video.images:
                    image.duration = duration_per_image

            video.status = "video_pending"
            db.session.commit()

            flash("Audio generated successfully!", "success")
            return redirect(url_for("generate_audio", video_id=video.id))

        except Exception as e:
            flash(f"Error generating audio: {str(e)}", "error")
            return redirect(url_for("generate_audio", video_id=video.id))

    return render_template(
        "generate_audio.html", video=video, script_data=script_data, speakers=speakers
    )