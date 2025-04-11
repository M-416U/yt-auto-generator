from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_from_directory,
)
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
                asset_description, image_file, image_style=video.image_style
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


# Add route to serve image files
# Update the file paths in image_routes.py
@app.route("/output_images/<path:filename>")
def serve_image(filename):
    return send_from_directory(os.path.abspath(app.config["OUTPUT_IMAGES"]), filename)


@app.route("/video/<int:video_id>/generate_single_image", methods=["POST"])
def generate_single_image(video_id, image_id):
    video = Video.query.get_or_404(video_id)
    image = Image.query.get_or_404(image_id)

    image_generator = AIImageGenerator()
    image_filename = f"video_{video.id}_image_{image.order+1}.png"
    image_file = os.path.join(app.config["OUTPUT_IMAGES"], image_filename)

    success = image_generator.download_image(
        image.prompt, image_file, image_style=video.image_style
    )

    if success:
        # Store relative path in database
        relative_path = os.path.join("output_images", image_filename)
        image.file_path = relative_path.replace("\\", "/")  # Ensure forward slashes
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "file_path": url_for("serve_image", filename=image_filename),
            }
        )
    else:
        return jsonify({"success": False, "error": "Failed to generate image"})


@app.route("/video/<int:video_id>/regenerate_image/<int:image_id>", methods=["POST"])
def regenerate_image(video_id, image_id):
    video = Video.query.get_or_404(video_id)
    image = Image.query.get_or_404(image_id)

    # Delete existing image if it exists
    if image.file_path and os.path.exists(image.file_path):
        try:
            os.remove(image.file_path)
        except:
            pass

    # Generate new image
    image_generator = AIImageGenerator()
    # Use absolute path for file storage
    image_file = os.path.join(
        app.config["OUTPUT_IMAGES"], f"video_{video.id}_image_{image.order+1}.png"
    )

    # Get updated prompt if provided
    new_prompt = request.form.get("prompt", image.prompt)
    image.prompt = new_prompt

    success = image_generator.download_image(
        new_prompt, image_file, image_style=video.image_style
    )

    if success:
        # Store relative path in database
        relative_path = f"output_images/video_{video.id}_image_{image.order+1}.png"
        image.file_path = relative_path
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "file_path": f"/output_images/video_{video.id}_image_{image.order+1}.png",
            }
        )
    else:
        return jsonify({"success": False, "error": "Failed to regenerate image"})


@app.route(
    "/video/<int:video_id>/update_image_animation/<int:image_id>", methods=["POST"]
)
def update_image_animation(video_id, image_id):
    image = Image.query.get_or_404(image_id)

    animation_type = request.form.get("animation_type", "fade")
    image.animation_type = animation_type
    db.session.commit()

    return jsonify({"success": True})


@app.route("/video/<int:video_id>/update_image_prompt/<int:image_id>", methods=["POST"])
def update_image_prompt(video_id, image_id):
    image = Image.query.get_or_404(image_id)
    new_prompt = request.form.get("prompt", "")

    if new_prompt:
        image.prompt = new_prompt
        db.session.commit()
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "No prompt provided"})
