import math
from typing import Dict, Any
import numpy as np

import moviepy.video.fx.all as vfx
from moviepy.editor import VideoClip, ImageClip
from utils import resize_and_crop_image
from PIL import Image


def apply_animation(
    clip: VideoClip,
    animation_type: str = "fade",
    duration: float = None,
    config: Dict[str, Any] = None,
) -> VideoClip:
    """
    Apply animation effects to a clip.

    Args:
        clip: The video clip to animate
        animation_type: Type of animation to apply
        duration: Duration of the clip
        config: Animation parameters

    Returns:
        Animated video clip
    """
    if duration is None:
        duration = clip.duration

    config = config or {}

    # Get the appropriate animation function
    animation_func = ANIMATIONS.get(animation_type)
    if not animation_func:
        print(
            f"Warning: Animation type '{animation_type}' not found. Using 'fade' instead."
        )
        animation_func = fade_animation

    # Apply the animation with config parameters
    return animation_func(clip, duration, **config)


def fade_animation(
    clip: VideoClip,
    duration: float,
    fade_in: float = 0.5,
    fade_out: float = 0.5,
    **kwargs,
) -> VideoClip:
    """Simple fade in/out animation."""
    return clip.fadein(fade_in).fadeout(fade_out)


def zoom_in_animation(
    clip: VideoClip,
    duration: float,
    zoom_start: float = 1.0,
    zoom_end: float = 1.2,
    **kwargs,
) -> VideoClip:
    """
    Zoom in from zoom_start to zoom_end scale without showing black edges.
    Uses dynamic cropping to maintain proper framing.
    """
    w, h = clip.size

    # Create a make_frame function that handles the zoom and cropping
    def make_frame(t):
        # Get original frame
        original_frame = clip.get_frame(t)

        # Calculate current zoom level
        progress = t / duration
        current_zoom = zoom_start + (zoom_end - zoom_start) * progress

        # Calculate new size based on zoom
        new_w = int(w * current_zoom)
        new_h = int(h * current_zoom)

        # Create a larger-than-needed frame with the original content scaled up
        from scipy.ndimage import zoom

        zoomed_frame = zoom(original_frame, (current_zoom, current_zoom, 1), order=1)

        # Crop the center to match original dimensions
        start_x = (zoomed_frame.shape[1] - w) // 2
        start_y = (zoomed_frame.shape[0] - h) // 2
        cropped_frame = zoomed_frame[start_y : start_y + h, start_x : start_x + w]

        return cropped_frame

    # Create a new clip with the zoomed frames
    new_clip = VideoClip(make_frame, duration=duration)
    new_clip = new_clip.set_duration(duration)

    # Carry over any audio from the original clip
    if clip.audio is not None:
        new_clip = new_clip.set_audio(clip.audio)

    return new_clip


def zoom_out_animation(
    clip: VideoClip,
    duration: float,
    zoom_start: float = 1.2,
    zoom_end: float = 1.0,
    **kwargs,
) -> VideoClip:
    """
    Zoom out from zoom_start to zoom_end scale without showing black edges.
    Uses dynamic cropping to maintain proper framing.
    """
    w, h = clip.size

    # Create a make_frame function that handles the zoom and cropping
    def make_frame(t):
        # Get original frame
        original_frame = clip.get_frame(t)

        # Calculate current zoom level
        progress = t / duration
        current_zoom = zoom_start - (zoom_start - zoom_end) * progress

        # Calculate new size based on zoom
        new_w = int(w * current_zoom)
        new_h = int(h * current_zoom)

        # Create a larger-than-needed frame with the original content scaled up
        from scipy.ndimage import zoom

        zoomed_frame = zoom(original_frame, (current_zoom, current_zoom, 1), order=1)

        # Crop the center to match original dimensions
        start_x = (zoomed_frame.shape[1] - w) // 2
        start_y = (zoomed_frame.shape[0] - h) // 2
        cropped_frame = zoomed_frame[start_y : start_y + h, start_x : start_x + w]

        return cropped_frame

    # Create a new clip with the zoomed frames
    new_clip = VideoClip(make_frame, duration=duration)
    new_clip = new_clip.set_duration(duration)

    # Carry over any audio from the original clip
    if clip.audio is not None:
        new_clip = new_clip.set_audio(clip.audio)

    return new_clip


def slide_animation(
    clip: VideoClip,
    duration: float = 0.5,
    transition_time: float = 0.5,
    direction: str = "horizontal",
    **kwargs,
) -> VideoClip:
    """Slide in/out animation."""

    if direction == "horizontal":
        position_func = lambda t: {
            "x": (
                (t / transition_time - 1) * clip.w
                if t < transition_time
                else (
                    0
                    if t < duration - transition_time
                    else ((t - (duration - transition_time)) / transition_time) * clip.w
                )
            ),
            "y": 0,
        }
    else:  # vertical
        position_func = lambda t: {
            "x": 0,
            "y": (
                (t / transition_time - 1) * clip.h
                if t < transition_time
                else (
                    0
                    if t < duration - transition_time
                    else ((t - (duration - transition_time)) / transition_time) * clip.h
                )
            ),
        }

    return clip.set_position(position_func)


def pulse_animation(
    clip: VideoClip,
    duration: float,
    scale_factor: float = 0.05,
    frequency: float = 2.0,
    **kwargs,
) -> VideoClip:
    """Pulsing/breathing animation."""
    w, h = clip.size

    # Create a make_frame function that handles the pulse and cropping
    def make_frame(t):
        # Get original frame
        original_frame = clip.get_frame(t)

        # Calculate current scale
        current_scale = 1 + scale_factor * math.sin(frequency * t * math.pi)

        # Create a larger-than-needed frame with the original content scaled
        from scipy.ndimage import zoom

        zoomed_frame = zoom(original_frame, (current_scale, current_scale, 1), order=1)

        # Crop the center to match original dimensions
        start_x = (zoomed_frame.shape[1] - w) // 2
        start_y = (zoomed_frame.shape[0] - h) // 2
        cropped_frame = zoomed_frame[start_y : start_y + h, start_x : start_x + w]

        return cropped_frame

    # Create a new clip with the pulsed frames
    new_clip = VideoClip(make_frame, duration=duration)
    new_clip = new_clip.set_duration(duration)

    # Carry over any audio from the original clip
    if clip.audio is not None:
        new_clip = new_clip.set_audio(clip.audio)

    return new_clip


def rotate_animation(
    clip: VideoClip, duration: float, max_angle: float = 5.0, **kwargs
) -> VideoClip:
    """Gentle rotation animation."""
    return clip.fx(
        vfx.rotate, lambda t: max_angle * math.sin(t * math.pi / duration), expand=False
    )


# Register all available animations
ANIMATIONS = {
    "fade": fade_animation,
    "zoom_in": zoom_in_animation,
    "zoom_out": zoom_out_animation,
    "slide": slide_animation,
    "pulse": pulse_animation,
    "rotate": rotate_animation,
}


def register_animation(name: str, animation_func):
    """Register a custom animation function."""
    ANIMATIONS[name] = animation_func


def create_animated_image_clip(
    image_file: str,
    width: int,
    height: int,
    duration: float,
    zoom_in: bool = True,
    zoom_factor: float = 1.5,
) -> VideoClip:
    """
    Create an animated image clip with proper zoom that prevents black edges.

    Args:
        image_file: Path to the image file
        width: Target width
        height: Target height
        duration: Duration of the clip
        zoom_in: Whether to zoom in (True) or out (False)
        zoom_factor: How much to zoom (1.5 = 150%)

    Returns:
        Animated image clip
    """
    # Open and convert image
    image = Image.open(image_file).convert("RGBA")

    # Resize image to be larger than needed while maintaining aspect ratio
    image = resize_and_crop_image(image, width, height)

    # Create a clip from the properly sized image
    image_clip = ImageClip(np.array(image.convert("RGB")), duration=duration)

    # Apply zoom animation
    if zoom_in:
        animated_clip = apply_animation(
            image_clip,
            animation_type="zoom_in",
            config={"zoom_start": 1.0, "zoom_end": zoom_factor},
        )
    else:
        animated_clip = apply_animation(
            image_clip,
            animation_type="zoom_out",
            config={"zoom_start": zoom_factor, "zoom_end": 1.0},
        )

    return animated_clip
