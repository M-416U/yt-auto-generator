from flask import request, jsonify
from app import app
from extensions import db
from models.models import Video, YouTubeShort, VideoUpload, ShortUpload
from models.youtube_account import YouTubeAccount
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import threading


# Unified API endpoint to upload videos/shorts to YouTube
@app.route("/api/upload/content", methods=["POST"])
def upload_content_to_youtube():
    data = request.json
    content_type = data.get("content_type")  # "video" or "short"
    content_id = data.get("content_id")
    account_ids = data.get("account_ids", [])
    title = data.get("title")
    description = data.get("description")
    tags = data.get("tags", "").split(",") if data.get("tags") else []
    privacy_status = data.get("privacy_status", "private")
    is_short = data.get("is_short", True)  # Default all uploads as shorts

    if not content_id or not account_ids:
        return jsonify({"success": False, "error": "Missing required parameters"}), 400

    # Get the content and file path based on content type
    if content_type == "video":
        content = Video.query.get_or_404(content_id)
        file_path = os.path.join(
            app.config["OUTPUT_FOLDER"], f"video_{content.id}_with_subs.mp4"
        )
    else:  # short
        content = YouTubeShort.query.get_or_404(content_id)
        file_path = (
            os.path.abspath(app.config["OUTPUT_FOLDER"]) + "/" + content.output_file
        )

    if not os.path.exists(file_path):
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"{content_type.capitalize()} file not found",
                }
            ),
            404,
        )

    # Create upload records for each account
    upload_ids = []
    for account_id in account_ids:
        if content_type == "video":
            upload = VideoUpload(
                video_id=content_id, account_id=account_id, upload_status="pending"
            )
        else:  # short
            upload = ShortUpload(
                short_id=content_id, account_id=account_id, upload_status="pending"
            )

        db.session.add(upload)
        db.session.commit()
        upload_ids.append(upload.id)

        # Start upload in background thread
        thread = threading.Thread(
            target=process_content_upload,
            args=(
                content_type,
                upload.id,
                file_path,
                title,
                description,
                tags,
                privacy_status,
                is_short,
            ),
        )
        thread.daemon = True
        thread.start()

    return jsonify(
        {
            "success": True,
            "message": f"Upload started for {len(account_ids)} accounts",
            "upload_ids": upload_ids,
            "content_type": content_type,
        }
    )


# API endpoint to check upload status
@app.route("/api/upload/status", methods=["POST"])
def check_upload_status():
    data = request.json
    content_type = data.get("type", "video")  # video or short
    upload_ids = data.get("upload_ids", [])

    if not upload_ids:
        return jsonify({"success": False, "error": "No upload IDs provided"}), 400

    statuses = []
    if content_type == "video":
        uploads = VideoUpload.query.filter(VideoUpload.id.in_(upload_ids)).all()
    else:
        uploads = ShortUpload.query.filter(ShortUpload.id.in_(upload_ids)).all()

    for upload in uploads:
        statuses.append(
            {
                "id": upload.id,
                "status": upload.upload_status,
                "youtube_id": upload.youtube_video_id,
                "error": upload.error_message,
            }
        )

    return jsonify({"success": True, "statuses": statuses})


# Unified background function to process content upload
def process_content_upload(
    content_type,
    upload_id,
    file_path,
    title,
    description,
    tags,
    privacy_status,
    is_short=True,
):
    with app.app_context():  # Add application context
        if content_type == "video":
            upload = VideoUpload.query.get(upload_id)
        else:  # short
            upload = ShortUpload.query.get(upload_id)

        if not upload:
            return

        try:
            upload.upload_status = "uploading"
            db.session.commit()

            account = YouTubeAccount.query.get(upload.account_id)
            if not account:
                raise Exception("YouTube account not found")

            # Create credentials object with all required fields
            credentials = Credentials(
                token=account.access_token,
                refresh_token=account.refresh_token,
                token_uri=account.token_uri,
                client_id=account.client_id,
                client_secret=account.client_secret,
                scopes=["https://www.googleapis.com/auth/youtube.upload"],
            )

            # Build YouTube API client
            youtube = build("youtube", "v3", credentials=credentials)

            # Prepare the request body
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": "22",
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False,
                    "shortForm": is_short,
                },
            }

            # Create MediaFileUpload object
            media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)

            # Execute the upload
            request = youtube.videos().insert(
                part=",".join(body.keys()), body=body, media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress() * 100)}%")

            # Update upload record with success
            upload.upload_status = "completed"
            upload.youtube_video_id = response["id"]
            db.session.commit()

        except Exception as e:
            # Update upload record with error
            upload.upload_status = "failed"
            upload.error_message = str(e)
            db.session.commit()
            print(f"Upload error: {str(e)}")