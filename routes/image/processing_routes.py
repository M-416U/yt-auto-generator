from flask import request, jsonify, url_for
from app import app
from extensions import db
from models.models import Video, Image
from image_generator import AIImageGenerator
import os

@app.route("/video/<int:video_id>/generate_single_image/<int:image_id>", methods=["POST"])
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