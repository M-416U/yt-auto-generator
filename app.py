import os
from flask import Flask, render_template
from extensions import db
import json

# models
from models.models import Video
from models.youtube_account import YouTubeAccount
from models.youtube_account import YouTubeStats
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY"
)  # Make sure this is set in your .env file
app.config["SESSION_TYPE"] = (
    "filesystem"  # Add this line for more reliable session storage
)
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour session lifetime
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
# Get the absolute base path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Use os.path.normpath to ensure consistent path separators
app.config["UPLOAD_FOLDER"] = os.path.normpath(
    os.path.join(BASE_DIR, "temp", "uploads")
)
app.config["OUTPUT_FOLDER"] = os.path.normpath(os.path.join(BASE_DIR, "temp", "output"))
app.config["OUTPUT_IMAGES"] = os.path.normpath(
    os.path.join(BASE_DIR, "temp", "output_images")
)
app.config["OUTPUT_AUDIOS"] = os.path.normpath(
    os.path.join(BASE_DIR, "temp", "output_audios")
)
app.config["TEMP_FOLDER"] = os.path.normpath(os.path.join(BASE_DIR, "temp", "temps"))

# Create directories if they don't exist
for directory in [
    app.config["UPLOAD_FOLDER"],
    app.config["OUTPUT_FOLDER"],
    app.config["OUTPUT_IMAGES"],
    app.config["OUTPUT_AUDIOS"],
    app.config["TEMP_FOLDER"],
]:
    os.makedirs(directory, exist_ok=True)

# Initialize extensions
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()


# Routes
@app.route("/")
def index():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return render_template("index.html", videos=videos)


# Import routes for each step
from routes.script_routes import *
from routes.image_routes import *
from routes.audio_routes import *
from routes.youtube_routes import *

from routes.upload_routes import *
from routes.video import *
from routes.shorts import *


@app.template_filter("file_exists")
def file_exists(path):
    return os.path.exists(path)


@app.template_filter("format_number")
def format_number(value):
    try:
        value = int(value)
        if value >= 1000000:
            return f"{value/1000000:.1f}M"
        elif value >= 1000:
            return f"{value/1000:.1f}K"
        return str(value)
    except:
        return "0"


@app.template_filter("fromjson")
def fromjson(value):
    try:
        return json.loads(value)
    except:
        return []


if __name__ == "__main__":
    app.run(debug=True)
