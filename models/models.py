from extensions import db
from datetime import datetime


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    topic = db.Column(db.String(100), nullable=False)
    video_type = db.Column(db.String(50), default="story")
    width = db.Column(db.Integer, default=720)
    height = db.Column(db.Integer, default=1280)
    duration = db.Column(db.Integer, default=60)
    status = db.Column(db.String(50), default="script_pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    script = db.relationship(
        "Script", backref="video", uselist=False, cascade="all, delete-orphan"
    )
    images = db.relationship("Image", backref="video", cascade="all, delete-orphan")
    image_style = db.Column(db.String(50), default="realistic")


class Script(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    audio_file = db.Column(db.String(255), nullable=True)
    audio_duration = db.Column(db.Float, default=0)


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id"), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    order = db.Column(db.Integer, nullable=False)
    animation_type = db.Column(db.String(50), default="fade")
    duration = db.Column(db.Float, default=0)
