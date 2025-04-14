from app import app, db
from app import Image
import os
from moviepy.editor import *
import animations
from PIL import Image as PILImage
from utils import resize_and_crop_image
import numpy as np
import threading
from datetime import datetime


# Helper functions
def get_video_path(video_id, with_subs=False):
    """Get the absolute path for a video file"""
    filename = (
        f"video_{video_id}_with_subs.mp4" if with_subs else f"video_{video_id}.mp4"
    )
    return os.path.normpath(os.path.join(app.config["OUTPUT_FOLDER"], filename))


def get_relative_video_path(video_id, with_subs=False):
    """Get the relative path for a video file to store in database"""
    filename = (
        f"video_{video_id}_with_subs.mp4" if with_subs else f"video_{video_id}.mp4"
    )
    return os.path.join("output", filename)


def get_audio_path(relative_path):
    """Get the absolute path for an audio file"""
    if not relative_path:
        return None
    filename = os.path.basename(relative_path)
    return os.path.normpath(os.path.join(app.config["OUTPUT_AUDIOS"], filename))


def get_image_path(relative_path):
    """Get the absolute path for an image file"""
    if not relative_path:
        return None
    filename = os.path.basename(relative_path)
    return os.path.normpath(os.path.join(app.config["OUTPUT_IMAGES"], filename))


def create_video_from_images_and_audio(video):
    try:
        # Get all images for this video
        images = Image.query.filter_by(video_id=video.id).order_by(Image.order).all()

        if not images:
            raise Exception("No images found for this video")

        # Get audio file path
        audio_file = get_audio_path(video.script.audio_file)
        if not audio_file or not os.path.exists(audio_file):
            raise Exception("Audio file not found")

        # Create video clips
        clips = []
        width = video.width
        height = video.height
        
        # Update progress to 10%
        video.progress = 10
        video.last_updated = datetime.utcnow()
        db.session.commit()

        total_images = len(images)
        for i, image in enumerate(images):
            image_path = get_image_path(image.file_path)
            if not image_path or not os.path.exists(image_path):
                continue

            duration = image.duration or 3.0  # Default duration if not set

            try:
                # Open and process image
                pil_image = PILImage.open(image_path).convert("RGBA")
                pil_image = resize_and_crop_image(pil_image, width, height)

                # Create clip
                image_clip = ImageClip(
                    np.array(pil_image.convert("RGB")), duration=duration
                )

                # Apply animation
                animation_type = image.animation_type or "fade"
                if animation_type in ["zoom_in", "zoom_out"]:
                    config = {
                        "zoom_start": 1.0 if animation_type == "zoom_in" else 1.5,
                        "zoom_end": 1.5 if animation_type == "zoom_in" else 1.0,
                    }
                    animated_clip = animations.apply_animation(
                        image_clip, animation_type=animation_type, config=config
                    )
                else:
                    animated_clip = animations.apply_animation(
                        image_clip, animation_type=animation_type
                    )

                clips.append(animated_clip)
                
                # Update progress (10-50% based on image processing)
                progress = 10 + int((i / total_images) * 40)
                video.progress = progress
                video.last_updated = datetime.utcnow()
                db.session.commit()
                
            except Exception as e:
                print(f"Error processing image {image_path}: {str(e)}")
                continue

        if not clips:
            raise Exception("No valid clips could be created")

        # Update progress to 50%
        video.progress = 50
        video.last_updated = datetime.utcnow()
        db.session.commit()

        # Create final video
        final_clip = concatenate_videoclips(clips, method="compose")
        audio_clip = AudioFileClip(audio_file)
        final_clip = final_clip.set_audio(audio_clip)

        # Update progress to 60%
        video.progress = 60
        video.last_updated = datetime.utcnow()
        db.session.commit()

        # Save video
        video_filename = get_video_path(video.id)
        
        # Update progress to 70%
        video.progress = 70
        video.last_updated = datetime.utcnow()
        db.session.commit()
        
        final_clip.write_videofile(
            video_filename,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=4,  # Utilize multiple CPU cores
            logger=None,  # Suppress moviepy logs
        )

        # Save the video path to the database
        video.video_path = get_relative_video_path(video.id)
        video.progress = 100
        video.last_updated = datetime.utcnow()
        db.session.commit()

        # Cleanup resources
        final_clip.close()
        audio_clip.close()
        for clip in clips:
            clip.close()

        return video_filename

    except Exception as e:
        # Ensure clips are closed even if an error occurs
        try:
            if "final_clip" in locals():
                final_clip.close()
            if "audio_clip" in locals():
                audio_clip.close()
            for clip in clips:
                clip.close()
        except:
            pass
        raise e


def cleanup_temp_files(video, keep_final=True):
    """Clean up all temporary files associated with a video"""
    try:
        # Clean up audio
        if video.script and video.script.audio_file:
            audio_path = get_audio_path(video.script.audio_file)
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                video.script.audio_file = None

        # Clean up images
        for image in video.images:
            if image.file_path:
                image_path = get_image_path(image.file_path)
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)
                    image.file_path = None

        # Clean up SRT file
        srt_path = os.path.join(app.config["OUTPUT_FOLDER"], f"video_{video.id}.srt")
        if os.path.exists(srt_path):
            os.remove(srt_path)

        # Handle video files
        video_path = get_video_path(video.id)
        video_with_subs_path = get_video_path(video.id, with_subs=True)

        if keep_final:
            if os.path.exists(video_with_subs_path) and os.path.exists(video_path):
                os.remove(video_path)
                # Keep only the path with subtitles in the database
                video.video_path = None
        else:
            for path in [video_path, video_with_subs_path]:
                if os.path.exists(path):
                    os.remove(path)
            # Clear both paths from the database
            video.video_path = None
            video.video_with_subs_path = None

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Error during cleanup: {str(e)}")
        raise


def create_video_in_background(video_id):
    """Create video in a background thread"""
    from models.models import Video  # Import here to avoid circular imports

    try:
        # Create application context for this thread
        with app.app_context():
            video = Video.query.get(video_id)
            if not video:
                print(f"Error: Video with ID {video_id} not found")
                return

            # Update status to processing
            video.status = "processing"
            video.progress = 0
            video.error_message = None
            video.last_updated = datetime.utcnow()
            db.session.commit()

            # Create the video
            create_video_from_images_and_audio(video)

            # Update status to captions_pending
            video.status = "captions_pending"
            db.session.commit()

            print(f"Video {video_id} created successfully in background")
    except Exception as e:
        # Update status to error
        try:
            with app.app_context():
                video = Video.query.get(video_id)
                if video:
                    video.status = "error"
                    video.error_message = str(e)[:255]  # Limit error message length
                    video.last_updated = datetime.utcnow()
                    db.session.commit()
        except Exception as inner_e:
            print(f"Error updating video status: {str(inner_e)}")
        print(f"Error creating video {video_id} in background: {str(e)}")


def start_video_creation_background(video):
    """Start video creation in a background thread"""
    thread = threading.Thread(target=create_video_in_background, args=(video.id,))
    thread.daemon = True
    thread.start()
    return thread
