from flask import jsonify
from app import app
from models.youtube_account import YouTubeAccount, YouTubeStats


# Add new route for fetching chart data
@app.route("/youtube/stats/<int:account_id>")
def youtube_stats(account_id):
    account = YouTubeAccount.query.get_or_404(account_id)

    # Get last 30 days of stats
    stats = (
        YouTubeStats.query.filter_by(account_id=account_id)
        .order_by(YouTubeStats.recorded_at.desc())
        .limit(30)
        .all()
    )

    # Get the most recent video stats
    latest_stats = stats[0] if stats else None
    video_stats = latest_stats.videos if latest_stats else []

    return jsonify({
        "stats": [
            {
                "date": stat.recorded_at.strftime("%Y-%m-%d"),
                "subscribers": stat.subscriber_count,
                "views": stat.view_count,
                "video_count": stat.video_count
            }
            for stat in reversed(stats)
        ],
        "videos": video_stats,
        "total_videos": latest_stats.video_count if latest_stats else 0
    })