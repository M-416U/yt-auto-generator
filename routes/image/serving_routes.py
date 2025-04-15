from flask import send_from_directory
from app import app
import os

# Add route to serve image files
@app.route("/output_images/<path:filename>")
def serve_image(filename):
    return send_from_directory(os.path.abspath(app.config["OUTPUT_IMAGES"]), filename)