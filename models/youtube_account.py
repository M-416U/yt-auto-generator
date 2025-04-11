from extensions import db
from datetime import datetime


class YouTubeAccount(db.Model):
    __tablename__ = "you_tube_account"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    channel_id = db.Column(db.String(255), unique=True, nullable=False)
    channel_title = db.Column(db.String(255), nullable=False)
    access_token = db.Column(db.String(255), nullable=False)
    refresh_token = db.Column(db.String(255), nullable=False)
    token_expiry = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_synced = db.Column(db.DateTime)
    # Channel statistics
    subscriber_count = db.Column(db.Integer, default=0)
    video_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)


class YouTubeStats(db.Model):
    __tablename__ = "youtube_stats"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer, db.ForeignKey("you_tube_account.id"), nullable=False
    )
    subscriber_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    video_count = db.Column(db.Integer, default=0)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    videos = db.Column(db.JSON, default=list)

    account = db.relationship("YouTubeAccount", backref="stats_history")
