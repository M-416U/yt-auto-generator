from flask import redirect, url_for, session, flash, render_template, request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app import app
from extensions import db
from models.youtube_account import YouTubeAccount
from models.youtube_account import YouTubeStats
from datetime import datetime, timedelta
import os
from flask import jsonify

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
]


@app.route("/youtube/auth")
def youtube_auth():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for("youtube_oauth2callback", _external=True),
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    session["state"] = state
    return redirect(authorization_url)


@app.route("/youtube/oauth2callback")
def youtube_oauth2callback():
    state = session["state"]
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for("youtube_oauth2callback", _external=True),
    )

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials

    # Get channel info
    youtube = build("youtube", "v3", credentials=credentials)
    channel_response = (
        youtube.channels().list(part="snippet,statistics", mine=True).execute()
    )

    channel = channel_response["items"][0]
    channel_id = channel["id"]

    try:
        # Check if account exists by user_id (Google account)
        account = YouTubeAccount.query.filter_by(user_id=credentials.client_id).first()
        print(account)
        if not account:
            # Create new account for this Google account
            account = YouTubeAccount(
                user_id=credentials.client_id,
                channel_id=channel_id,
                channel_title=channel["snippet"]["title"],
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expiry=datetime.utcnow()
                + timedelta(seconds=credentials.expiry.second),
                subscriber_count=channel["statistics"]["subscriberCount"],
                video_count=channel["statistics"]["videoCount"],
                view_count=channel["statistics"]["viewCount"],
            )
            db.session.add(account)
        else:
            # Check if this is a different channel for the same account
            if account.channel_id != channel_id:
                # Create new account entry for this channel
                new_channel = YouTubeAccount(
                    user_id=credentials.client_id,
                    channel_id=channel_id,
                    channel_title=channel["snippet"]["title"],
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_expiry=datetime.utcnow()
                    + timedelta(seconds=credentials.expiry.second),
                    subscriber_count=channel["statistics"]["subscriberCount"],
                    video_count=channel["statistics"]["videoCount"],
                    view_count=channel["statistics"]["viewCount"],
                )
                db.session.add(new_channel)
            else:
                # Update existing channel
                account.channel_title = channel["snippet"]["title"]
                account.access_token = credentials.token
                account.refresh_token = credentials.refresh_token
                account.token_expiry = datetime.utcnow() + timedelta(
                    seconds=credentials.expiry.second
                )
                account.last_synced = datetime.utcnow()
                account.subscriber_count = channel["statistics"]["subscriberCount"]
                account.video_count = channel["statistics"]["videoCount"]
                account.view_count = channel["statistics"]["viewCount"]

        db.session.commit()
        flash("Successfully connected YouTube channel!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error connecting YouTube account: {str(e)}", "error")
        print(f"Error: {str(e)}")

    return redirect(url_for("youtube_accounts"))


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
        db.session.delete(account)
        db.session.commit()
        flash("YouTube channel successfully disconnected!", "success")
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        flash(f"Error disconnecting channel: {str(e)}", "error")
        return jsonify({"success": False, "error": str(e)}), 400


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
