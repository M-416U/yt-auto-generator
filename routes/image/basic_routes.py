from flask import render_template, request, redirect, url_for, flash
from app import app
from extensions import db
from models.models import Video, Image
from image_generator import AIImageGenerator
import json
import os


# Step 2: Image Generation
@app.route("/video/<int:video_id>/generate_images", methods=["GET", "POST"])
def generate_images(video_id):
    video = Video.query.get_or_404(video_id)

    if not video.script:
        flash("No script found. Please generate a script first.", "error")
        return redirect(url_for("generate_script", video_id=video.id))

    script_data = json.loads(video.script.content)

    if request.method == "POST":
        # Clear existing images
        for image in video.images:
            if image.file_path and os.path.exists(image.file_path):
                try:
                    os.remove(image.file_path)
                except:
                    pass

        Image.query.filter_by(video_id=video.id).delete()
        # Generate new images
        image_generator = AIImageGenerator()

        for i, asset_description in enumerate(script_data.get("assets", [])):
            if not asset_description or not asset_description.strip():
                continue
            image_file = os.path.join(
                app.config["OUTPUT_IMAGES"], f"video_{video.id}_image_{i+1}.png"
            )

            # Generate image
            success = image_generator.download_image(
                asset_description,
                image_file,
                image_style=video.image_style,
                use_ir=True,
            )

            # Get animation type from form
            animation_type = request.form.get(f"animation_{i}", "fade")

            # Create image record - store relative path for database
            relative_path = f"output_images/video_{video.id}_image_{i+1}.png"
            image = Image(
                video_id=video.id,
                prompt=asset_description,
                order=i,
                animation_type=animation_type,
                file_path=relative_path if success else None,
            )
            db.session.add(image)

        # Update video status
        video.status = "audio_pending"
        db.session.commit()

        flash("Image generation started!", "success")
        return redirect(url_for("process_images", video_id=video.id))

    # Create enumerated assets list for the template
    assets_with_index = []
    for i, asset in enumerate(script_data.get("assets", [])):
        assets_with_index.append((i, asset))

    return render_template(
        "generate_images.html",
        video=video,
        script_data=script_data,
        assets_with_index=assets_with_index,
    )


@app.route("/video/<int:video_id>/process_images")
def process_images(video_id):
    video = Video.query.get_or_404(video_id)
    return render_template("process_images.html", video=video)
