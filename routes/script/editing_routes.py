from flask import render_template, request, redirect, url_for, flash
from app import app
from extensions import db
from models.models import Video
from generate_script import GeminiVideoScriptGenerator
import json


@app.route("/video/<int:video_id>/edit_script", methods=["GET", "POST"])
def edit_script(video_id):
    video = Video.query.get_or_404(video_id)

    if not video.script:
        flash("No script found. Please generate a script first.", "error")
        return redirect(url_for("generate_script", video_id=video.id))

    script_data = json.loads(video.script.content)

    if request.method == "POST":
        action = request.form.get("action", "save")

        if action == "regenerate":
            # Regenerate script using Gemini
            generator = GeminiVideoScriptGenerator()
            new_script_data = generator.generate_video_script(
                video.topic, video.video_type, duration=video.duration
            )

            if not new_script_data:
                flash("Failed to regenerate script. Please try again.", "error")
                return redirect(url_for("edit_script", video_id=video.id))

            # Update video with new title and description
            video.title = new_script_data.get("title", f"Video about {video.topic}")
            video.description = new_script_data.get("desc", "No description available")
            video.script.content = json.dumps(new_script_data)
            db.session.commit()

            flash("Script regenerated successfully!", "success")
            return redirect(url_for("edit_script", video_id=video.id))

        # Regular save action
        title = request.form.get("title")
        description = request.form.get("description")

        script_lines = []
        asset_descriptions = []

        # Get all script lines and asset descriptions from form
        i = 0
        while f"script_{i}" in request.form:
            script_line = request.form.get(f"script_{i}")
            if script_line.strip():
                script_lines.append(script_line)

                # Get corresponding asset description
                asset_desc = request.form.get(f"asset_{i}", "")
                asset_descriptions.append(asset_desc)
            i += 1

        # Update script data
        script_data["title"] = title
        script_data["desc"] = description
        script_data["script"] = script_lines
        script_data["assets"] = asset_descriptions

        # Save updated script
        video.script.content = json.dumps(script_data)
        db.session.commit()

        flash("Script updated successfully!", "success")
        return redirect(url_for("generate_images", video_id=video.id))

    return render_template("edit_script.html", video=video, script_data=script_data)