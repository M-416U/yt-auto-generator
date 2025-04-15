from flask import render_template
from app import app
from models.models import VideoUpload, ShortUpload


# Route to view all uploads
@app.route("/uploads")
def view_uploads():
    video_uploads = VideoUpload.query.order_by(VideoUpload.upload_date.desc()).all()
    short_uploads = ShortUpload.query.order_by(ShortUpload.upload_date.desc()).all()

    return render_template(
        "upload/uploads_list.html",
        video_uploads=video_uploads,
        short_uploads=short_uploads,
    )