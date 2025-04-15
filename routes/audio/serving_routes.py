from flask import send_from_directory
from app import app
import os


@app.route("/output_audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(
        os.path.abspath(app.config["OUTPUT_AUDIOS"]), filename, mimetype="audio/wav"
    )