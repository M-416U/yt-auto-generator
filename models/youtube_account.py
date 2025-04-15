from extensions import db
from datetime import datetime
import json


class YouTubeAccount(db.Model):
    __tablename__ = "you_tube_account"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)  # Google account ID
    channel_id = db.Column(db.String(255), nullable=False)  # YouTube channel ID
    channel_title = db.Column(db.String(255), nullable=False)
    
    # OAuth credentials
    access_token = db.Column(db.String(255), nullable=False)
    refresh_token = db.Column(db.String(255), nullable=False)
    token_expiry = db.Column(db.DateTime, nullable=False)
    token_uri = db.Column(db.String(255), default="https://oauth2.googleapis.com/token")
    client_id = db.Column(db.String(255), nullable=True)
    client_secret = db.Column(db.String(255), nullable=True)
    
    # Channel statistics
    subscriber_count = db.Column(db.Integer, default=0)
    video_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_synced = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships defined in models.py (VideoUpload and ShortUpload)
    
    def to_dict(self):
        """Convert account to dictionary for API responses"""
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'channel_title': self.channel_title,
            'subscriber_count': self.subscriber_count,
            'video_count': self.video_count,
            'view_count': self.view_count,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None
        }

class YouTubeStats(db.Model):
    """Model to store historical YouTube channel statistics"""
    id = db.Column(db.Integer, primary_key=True)
    # Change the foreign key reference to match the actual table name
    account_id = db.Column(db.Integer, db.ForeignKey('you_tube_account.id'), nullable=False)
    subscriber_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    video_count = db.Column(db.Integer, default=0)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    videos = db.Column(db.Text, nullable=True)  # JSON string of video stats
    
    account = db.relationship("YouTubeAccount", backref="stats_history")
    
    def get_videos(self):
        """Get videos data as Python objects"""
        if self.videos:
            return json.loads(self.videos)
        return []
