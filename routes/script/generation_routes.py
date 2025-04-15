from flask import render_template, request, redirect, url_for, flash
from app import app
from extensions import db
from models.models import Video, Script
from generate_script import GeminiVideoScriptGenerator
import json


# Step 1: Script Generation
@app.route("/video/<int:video_id>/generate_script", methods=["GET", "POST"])
def generate_script(video_id):
    video = Video.query.get_or_404(video_id)

    if request.method == "POST":
        # Generate script using Gemini
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

        if not script_data:
            flash("Failed to generate script. Please try again.", "error")
            return redirect(url_for("generate_script", video_id=video.id))

        # Update video with real title and description
        video.title = script_data.get("title", f"Video about {video.main_idea}")
        video.description = script_data.get("desc", "No description available")

        # Save script to database
        if video.script:
            video.script.content = json.dumps(script_data)
        else:
            script = Script(video_id=video.id, content=json.dumps(script_data))
            db.session.add(script)

        video.status = "images_pending"
        db.session.commit()

        flash("Script generated successfully!", "success")
        return redirect(url_for("generate_images", video_id=video.id))

    return render_template("generate_script.html", video=video)