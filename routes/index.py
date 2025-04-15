import os
from flask import render_template
from app import app

from models.models import ShortUpload, Video, VideoUpload, YouTubeShort
from models.youtube_account import YouTubeAccount
from models.youtube_account import YouTubeStats


@app.route("/")
def index():
    # Get videos with sorting
    videos = Video.query.order_by(Video.created_at.desc()).all()

    # Get shorts data
    shorts = YouTubeShort.query.order_by(YouTubeShort.created_at.desc()).limit(5).all()
    shorts_count = YouTubeShort.query.count()

    # Get YouTube accounts
    youtube_accounts = YouTubeAccount.query.all()

    # Get upload statistics
    video_uploads = VideoUpload.query.count()
    short_uploads = ShortUpload.query.count()

    # Calculate status statistics for videos
    video_stats = {
        "total": len(videos),
        "completed": sum(1 for v in videos if v.status == "completed"),
        "pending": sum(1 for v in videos if "pending" in v.status),
        "processing": sum(1 for v in videos if v.status == "processing"),
        "failed": sum(1 for v in videos if "failed" in v.status),
    }

    # Calculate status statistics for shorts
    shorts_stats = {
        "total": shorts_count,
        "completed": YouTubeShort.query.filter_by(status="completed").count(),
        "processing": YouTubeShort.query.filter_by(status="processing").count(),
        "failed": YouTubeShort.query.filter_by(status="failed").count(),
        "pending": YouTubeShort.query.filter_by(status="pending").count(),
    }

    # Get recent uploads
    recent_uploads = (
        VideoUpload.query.order_by(VideoUpload.upload_date.desc()).limit(5).all()
    )
    recent_short_uploads = (
        ShortUpload.query.order_by(ShortUpload.upload_date.desc()).limit(5).all()
    )

    return render_template(
        "index.html",
        videos=videos,
        shorts=shorts,
        shorts_count=shorts_count,
        youtube_accounts=youtube_accounts,
        video_stats=video_stats,
        shorts_stats=shorts_stats,
        video_uploads=video_uploads,
        short_uploads=short_uploads,
        recent_uploads=recent_uploads,
        recent_short_uploads=recent_short_uploads,
    )
