import json
from flask import redirect, url_for, session, flash, request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app import app
from extensions import db
from models.youtube_account import YouTubeAccount
from datetime import datetime, timedelta
import os
import oauthlib.oauth2.rfc6749.errors

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

    try:
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

        # Get client ID and client secret from the client secrets file
        client_info = {}
        try:
            with open(CLIENT_SECRETS_FILE, "r") as f:
                client_secrets = json.load(f)
                if "web" in client_secrets:
                    client_info = client_secrets["web"]
                elif "installed" in client_secrets:
                    client_info = client_secrets["installed"]
        except Exception as e:
            print(f"Error reading client secrets: {str(e)}")

        try:
            # Check if account exists by user_id (Google account)
            account = YouTubeAccount.query.filter_by(
                user_id=credentials.client_id
            ).first()

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
                    token_uri=credentials.token_uri,
                    client_id=client_info.get("client_id"),
                    client_secret=client_info.get("client_secret"),
                    subscriber_count=channel["statistics"]["subscriberCount"],
                    video_count=channel["statistics"]["videoCount"],
                    view_count=channel["statistics"]["viewCount"],
                )
                db.session.add(account)
            else:
                # Update existing account
                account.channel_title = channel["snippet"]["title"]
                account.access_token = credentials.token
                account.refresh_token = credentials.refresh_token
                account.token_expiry = datetime.utcnow() + timedelta(
                    seconds=credentials.expiry.second
                )
                account.token_uri = credentials.token_uri
                account.client_id = client_info.get("client_id")
                account.client_secret = client_info.get("client_secret")
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
    except oauthlib.oauth2.rfc6749.errors.AccessDeniedError:
        flash(
            "Access denied. Please grant the required permissions to connect your YouTube account.",
            "error",
        )
        return redirect(url_for("youtube_accounts"))
    except Exception as e:
        flash(f"Error connecting YouTube account: {str(e)}", "error")
        return redirect(url_for("youtube_accounts"))
