from flask import render_template, flash, jsonify
from app import app
from extensions import db
from models.youtube_account import YouTubeAccount, YouTubeStats
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
]


@app.route("/youtube/accounts")
def youtube_accounts():
    accounts = YouTubeAccount.query.all()
    accounts_with_stats = []

    for account in accounts:
        try:
            # Create credentials object
            credentials = Credentials(
                token=account.access_token,
                refresh_token=account.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=account.user_id,
                scopes=SCOPES,
            )

            # Get updated channel info
            youtube = build("youtube", "v3", credentials=credentials)
            
            # Get channel statistics
            channel_response = (
                youtube.channels()
                .list(part="snippet,statistics", id=account.channel_id)
                .execute()
            )

            if channel_response["items"]:
                channel = channel_response["items"][0]
                
                # Update account with latest stats
                account.subscriber_count = int(channel["statistics"]["subscriberCount"])
                account.video_count = int(channel["statistics"]["videoCount"])
                account.view_count = int(channel["statistics"]["viewCount"])
                account.last_synced = datetime.utcnow()
                
                # Get recent videos statistics
                videos_response = youtube.search().list(
                    part="id",
                    channelId=account.channel_id,
                    maxResults=10,
                    order="date",
                    type="video"
                ).execute()

                video_stats = []
                if videos_response.get("items"):
                    video_ids = [item["id"]["videoId"] for item in videos_response["items"]]
                    videos_details = youtube.videos().list(
                        part="snippet,statistics",
                        id=",".join(video_ids)
                    ).execute()

                    for video in videos_details.get("items", []):
                        video_stats.append({
                            "id": video["id"],
                            "title": video["snippet"]["title"],
                            "views": int(video["statistics"].get("viewCount", 0)),
                            "likes": int(video["statistics"].get("likeCount", 0)),
                            "comments": int(video["statistics"].get("commentCount", 0)),
                            "published_at": video["snippet"]["publishedAt"]
                        })

                # Add historical data point with video stats
                stats = YouTubeStats(
                    account_id=account.id,
                    subscriber_count=account.subscriber_count,
                    view_count=account.view_count,
                    video_count=account.video_count,
                    videos=video_stats
                )
                db.session.add(stats)
                accounts_with_stats.append(account)

        except Exception as e:
            print(f"Error updating account {account.channel_title}: {str(e)}")
            accounts_with_stats.append(account)
            continue

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error saving updates: {str(e)}")

    return render_template("youtube/accounts.html", accounts=accounts_with_stats)


@app.route("/youtube/account/<int:account_id>")
def youtube_account_details(account_id):
    account = YouTubeAccount.query.get_or_404(account_id)
    return render_template("youtube/account_details.html", account=account)


@app.route("/youtube/disconnect/<int:account_id>", methods=["POST"])
def youtube_disconnect(account_id):
    try:
        account = YouTubeAccount.query.get_or_404(account_id)
        
        # First, check if there are any uploads associated with this account
        from models.models import VideoUpload, ShortUpload
        
        video_uploads = VideoUpload.query.filter_by(account_id=account_id).all()
        short_uploads = ShortUpload.query.filter_by(account_id=account_id).all()
        
        if video_uploads or short_uploads:
            # Option 1: Delete the associated uploads
            for upload in video_uploads:
                db.session.delete(upload)
                
            for upload in short_uploads:
                db.session.delete(upload)
                
            # Option 2 (alternative): Set uploads to a placeholder account or null
            # This would require modifying your database schema to allow NULL values
            # for upload.account_id or creating a placeholder account
            
            # Commit these changes first
            db.session.commit()
        
        # Now delete the account
        db.session.delete(account)
        db.session.commit()
        
        flash("YouTube channel successfully disconnected!", "success")
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        flash(f"Error disconnecting channel: {str(e)}", "error")
        return jsonify({"success": False, "error": str(e)}), 400