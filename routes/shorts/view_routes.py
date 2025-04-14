from flask import render_template, redirect, url_for, flash, send_file
from app import app
from extensions import db
from models.models import YouTubeSource, YouTubeShort
import os


@app.route("/shorts/source/<int:source_id>")
def view_shorts_source(source_id):
    source = YouTubeSource.query.get_or_404(source_id)
    shorts = YouTubeShort.query.filter_by(youtube_source_id=source_id).all()

    # Check if processing is complete
    processing_complete = all(short.status != "processing" for short in shorts)

    # Get the first completed short to display by default
    selected_short = None
    for short in shorts:
        if short.status == "completed":
            selected_short = short
            break

    return render_template(
        "view_shorts_source.html",
        source=source,
        shorts=shorts,
        processing_complete=processing_complete,
        selected_short=selected_short,
        selected_short_id=selected_short.id if selected_short else None,
    )


@app.route("/shorts/source/<int:source_id>/short/<int:short_id>")
def view_short_in_source(source_id, short_id):
    source = YouTubeSource.query.get_or_404(source_id)
    shorts = YouTubeShort.query.filter_by(youtube_source_id=source_id).all()
    selected_short = YouTubeShort.query.get_or_404(short_id)

    # Ensure the short belongs to this source
    if selected_short.youtube_source_id != source_id:
        flash("This short does not belong to the selected source", "error")
        return redirect(url_for("view_shorts_source", source_id=source_id))

    # Check if processing is complete
    processing_complete = all(short.status != "processing" for short in shorts)

    return render_template(
        "view_shorts_source.html",
        source=source,
        shorts=shorts,
        processing_complete=processing_complete,
        selected_short=selected_short,
        selected_short_id=short_id,
    )


@app.route("/shorts/view/<int:short_id>")
def view_short(short_id):
    short = YouTubeShort.query.get_or_404(short_id)
    return render_template("view_short.html", short=short)


@app.route("/shorts/download/<int:short_id>")
def download_short(short_id):
    short = YouTubeShort.query.get_or_404(short_id)

    if not short.output_file:
        flash("Short video file not found", "error")
        return redirect(url_for("view_short", short_id=short.id))

    video_path = os.path.join(app.config["OUTPUT_FOLDER"], short.output_file)

    if not os.path.exists(video_path):
        flash("Short video file not found", "error")
        return redirect(url_for("view_short", short_id=short.id))

    return send_file(video_path, as_attachment=True, download_name=f"{short.title}.mp4")


@app.route("/shorts/source/<int:source_id>/delete", methods=["POST"])
def delete_shorts_source(source_id):
    source = YouTubeSource.query.get_or_404(source_id)

    try:
        # Delete all associated shorts first
        shorts = YouTubeShort.query.filter_by(youtube_source_id=source_id).all()

        # Delete video files if they exist
        for short in shorts:
            if short.output_file:
                video_path = os.path.join(
                    app.config["OUTPUT_FOLDER"], short.output_file
                )
                if os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except Exception as e:
                        print(f"Error deleting file {video_path}: {str(e)}")

            db.session.delete(short)

        # Delete the source
        db.session.delete(source)
        db.session.commit()

        flash("YouTube source and all associated shorts have been deleted", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting source: {str(e)}", "error")

    return redirect(url_for("all_shorts_sources"))


@app.route("/shorts/delete/<int:short_id>", methods=["POST"])
def delete_short_from_source(short_id):
    short = YouTubeShort.query.get_or_404(short_id)
    source_id = short.youtube_source_id

    try:
        # Delete video file if it exists
        if short.output_file:
            video_path = os.path.join(app.config["OUTPUT_FOLDER"], short.output_file)
            if os.path.exists(video_path):
                try:
                    os.remove(video_path)
                except Exception as e:
                    print(f"Error deleting file {video_path}: {str(e)}")

        # Delete the short from database
        db.session.delete(short)
        db.session.commit()

        flash("Short has been deleted successfully", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting short: {str(e)}", "error")

    return redirect(url_for("view_shorts_source", source_id=source_id))