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

    with open("voice_overs.json", "r", encoding="utf8") as f:
        voice_overs = json.load(f)

    script_data = json.loads(video.script.content)

    if request.method == "POST":
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
            selected_speaker = request.form.get("speaker", "1")
            selected_language = request.form.get("language", "en")

            audio_file, total_duration = text_to_speech(
                script_text,
                output_dir=app.config["OUTPUT_AUDIOS"],
                speaker=selected_speaker,
                language=selected_language,
            )

            if not audio_file:
                flash("Failed to generate audio. Please try again.", "error")
                return redirect(url_for("generate_audio", video_id=video.id))

            filename = os.path.basename(audio_file)
            video.script.audio_file = f"{filename}"
            video.script.audio_duration = total_duration

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
        "generate_audio.html",
        video=video,
        script_data=script_data,
        voice_overs=voice_overs,
    )
