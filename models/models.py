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
    tone = db.Column(db.String(50), default="conversational")
    writing_style = db.Column(db.String(50), default="direct")
    niche = db.Column(db.String(50), nullable=True)
    main_idea = db.Column(db.Text, nullable=True)
    uploads = db.relationship("VideoUpload", backref="video", lazy=True)
    youtube_source_id = db.Column(
        db.Integer, db.ForeignKey("you_tube_source.id"), nullable=True
    )
    source_timestamp = db.Column(db.String(50), nullable=True)
    # New fields for video paths and progress tracking
    video_path = db.Column(db.String(255), nullable=True)
    video_with_subs_path = db.Column(db.String(255), nullable=True)
    progress = db.Column(db.Integer, default=0)  # Progress percentage (0-100)
    error_message = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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


# Add after existing models


class YouTubeSource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255))
    transcript = db.Column(db.Text)
    language = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    videos = db.relationship("Video", backref="youtube_source", lazy=True)
    shorts = db.relationship("YouTubeShort", backref="youtube_source", lazy=True)


# New model for YouTube Shorts
class YouTubeShort(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    youtube_source_id = db.Column(
        db.Integer, db.ForeignKey("you_tube_source.id"), nullable=False
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    viral_potential = db.Column(db.Text)
    duration_seconds = db.Column(db.Integer)
    hashtags = db.Column(db.Text)  # Stored as JSON string
    hook = db.Column(db.Text)
    viral_score = db.Column(db.Integer)
    start_time = db.Column(db.Float)
    end_time = db.Column(db.Float)
    transcript = db.Column(db.Text)
    status = db.Column(
        db.String(50), default="pending"
    )  # pending, processing, completed, failed
    output_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    selected = db.Column(
        db.Boolean, default=True
    )  # To track if user selected this short
    # Add relationship to track uploads
    uploads = db.relationship("ShortUpload", backref="short", lazy=True)


# New model to track video uploads to YouTube
class VideoUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id"), nullable=False)
    account_id = db.Column(
        db.Integer, db.ForeignKey("you_tube_account.id"), nullable=False
    )
    youtube_video_id = db.Column(
        db.String(255), nullable=True
    )  # YouTube's video ID after upload
    upload_status = db.Column(
        db.String(50), default="pending"
    )  # pending, uploading, completed, failed
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    error_message = db.Column(db.Text, nullable=True)

    # Relationship to YouTube account
    account = db.relationship("YouTubeAccount", backref="video_uploads")


# New model to track short uploads to YouTube
class ShortUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    short_id = db.Column(db.Integer, db.ForeignKey("you_tube_short.id"), nullable=False)
    account_id = db.Column(
        db.Integer, db.ForeignKey("you_tube_account.id"), nullable=False
    )
    youtube_video_id = db.Column(
        db.String(255), nullable=True
    )  # YouTube's video ID after upload
    upload_status = db.Column(
        db.String(50), default="pending"
    )  # pending, uploading, completed, failed
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    error_message = db.Column(db.Text, nullable=True)

    # Relationship to YouTube account
    account = db.relationship("YouTubeAccount", backref="short_uploads")
