"""
Video Composer Module - Updated to use layout_config.json
Creates vocabulary videos with exact layout specifications
"""

import subprocess
import json
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import textwrap
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.layout_config import get_layout_config


def find_font_file(font_name: str, bold: bool = False) -> Optional[Path]:
    """Find font file on system."""
    font_locations = [
        Path("/usr/share/fonts"),
        Path("/System/Library/Fonts"),
        Path("C:/Windows/Fonts"),
        Path.home() / ".fonts",
    ]
    
    # Font name variations to try
    variations = [
        f"{font_name}.ttf",
        f"{font_name.lower()}.ttf",
        f"{font_name.replace(' ', '')}.ttf",
        f"{font_name.replace(' ', '-')}.ttf",
        f"{font_name.replace(' ', '')}{'Bold' if bold else 'Regular'}.ttf",
    ]
    
    for location in font_locations:
        if location.exists():
            for var in variations:
                for font_file in location.rglob(var):
                    return font_file
    
    return None


def get_font(size: int, bold: bool = False, font_family: str = None) -> ImageFont.FreeTypeFont:
    """
    Get font with fallback chain.
    
    Args:
        size: Font size
        bold: Whether to use bold variant
        font_family: Font family name (None uses layout config)
    
    Returns:
        ImageFont object
    """
    layout = get_layout_config()
    
    if font_family is None:
        font_family = layout.font_family
    
    # Try primary font
    font_file = find_font_file(font_family, bold)
    if font_file:
        try:
            return ImageFont.truetype(str(font_file), size)
        except:
            pass
    
    # Try fallback fonts
    for fallback in layout.fallback_fonts:
        font_file = find_font_file(fallback, bold)
        if font_file:
            try:
                return ImageFont.truetype(str(font_file), size)
            except:
                continue
    
    # System defaults
    default_fonts = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "arial.ttf",
    ]
    
    for font_name in default_fonts:
        try:
            return ImageFont.truetype(font_name, size)
        except:
            continue
    
    # Final fallback
    return ImageFont.load_default()


def remove_background(image: Image.Image, threshold: int = 240) -> Image.Image:
    """
    Remove white/light background from image and make it transparent.
    
    Args:
        image: Input image
        threshold: RGB threshold for considering a pixel as "white" (0-255)
    
    Returns:
        Image with transparent background
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    data = image.getdata()
    new_data = []
    
    for item in data:
        # If pixel is mostly white, make it transparent
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            new_data.append((255, 255, 255, 0))  # Transparent
        else:
            new_data.append(item)
    
    image.putdata(new_data)
    return image


def draw_text_centered(draw: ImageDraw.Draw, text: str, y: int,
                       font: ImageFont.FreeTypeFont, color: tuple,
                       max_width: int, center_x: int,
                       line_spacing: float = 1.2) -> int:
    """
    Draw text centered at given Y position with automatic wrapping.
    
    Args:
        draw: ImageDraw object
        text: Text to draw
        y: Y position (top)
        font: Font to use
        color: RGB color tuple
        max_width: Maximum width for text wrapping
        center_x: X coordinate of center
        line_spacing: Line spacing multiplier
    
    Returns:
        Y coordinate after last line (for stacking elements)
    """
    # Get text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # If text fits on one line
    if text_width <= max_width:
        x = center_x - (text_width // 2)
        draw.text((x, y), text, font=font, fill=color)
        return y + text_height
    
    # Text needs wrapping
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        test_bbox = draw.textbbox((0, 0), test_line, font=font)
        test_width = test_bbox[2] - test_bbox[0]
        
        if test_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Draw each line
    line_height = int(text_height * line_spacing)
    current_y = y
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = center_x - (line_width // 2)
        draw.text((x, current_y), line, font=font, fill=color)
        current_y += line_height
    
    return current_y


def create_video_frame(word: str, definition: str, image_path: Optional[Path] = None,
                       output_path: Optional[Path] = None) -> Path:
    """
    Create video frame following layout_config.json specifications.
    
    Args:
        word: Vocabulary word
        definition: Word definition
        image_path: Path to illustration image (optional)
        output_path: Where to save frame (optional)
    
    Returns:
        Path to generated frame
    """
    layout = get_layout_config()
    
    # Create canvas
    canvas = Image.new("RGBA", layout.canvas_size, layout.background_color + (255,))
    draw = ImageDraw.Draw(canvas)
    
    # Load fonts
    word_config = layout.word_title
    def_config = layout.definition
    brand_config = layout.branding
    
    font_word = get_font(
        word_config['font_size'],
        bold=(word_config['font_weight'] == 'bold')
    )
    
    font_definition = get_font(
        def_config['font_size'],
        bold=(def_config['font_weight'] == 'bold')
    )
    
    font_branding = get_font(
        brand_config['font_size'],
        bold=(brand_config['font_weight'] == 'bold')
    )
    
    # ===========================================
    # DRAW WORD TITLE
    # ===========================================
    # Use individual margins if available, otherwise fall back to safe area
    word_left = word_config.get('left_margin', layout.safe_left)
    word_right = word_config.get('right_margin', layout.canvas_width - layout.safe_right)
    word_width = layout.canvas_width - word_left - word_right
    word_center_x = word_left + (word_width // 2)
    
    draw_text_centered(
        draw=draw,
        text=word.capitalize(),
        y=word_config['y_start'] + 10,  # Small padding
        font=font_word,
        color=tuple(word_config['color']),
        max_width=word_width,
        center_x=word_center_x
    )
    
    # ===========================================
    # DRAW DEFINITION
    # ===========================================
    # Use individual margins if available, otherwise fall back to safe area
    def_left = def_config.get('left_margin', layout.safe_left)
    def_right = def_config.get('right_margin', layout.canvas_width - layout.safe_right)
    def_width = layout.canvas_width - def_left - def_right
    def_center_x = def_left + (def_width // 2)
    
    draw_text_centered(
        draw=draw,
        text=definition,
        y=def_config['y_start'] + 5,  # Small padding
        font=font_definition,
        color=tuple(def_config['color']),
        max_width=def_width - 40,  # Extra padding for readability
        center_x=def_center_x,
        line_spacing=def_config.get('line_spacing', 1.2)
    )
    
    # ===========================================
    # DRAW IMAGE
    # ===========================================
    if image_path and Path(image_path).exists():
        try:
            vocab_image = Image.open(image_path)
            
            # Ensure RGBA
            if vocab_image.mode != "RGBA":
                vocab_image = vocab_image.convert("RGBA")
            
            # Remove background if configured
            if layout.image['transparent_bg']:
                vocab_image = remove_background(vocab_image, threshold=235)
            
            # Resize to fit within specified dimensions
            img_config = layout.image
            max_width = img_config['max_width']
            max_height = img_config['height']
            
            # Calculate scaling
            scale = min(
                max_width / vocab_image.width,
                max_height / vocab_image.height,
                1.0  # Don't upscale
            )
            
            new_size = (
                int(vocab_image.width * scale),
                int(vocab_image.height * scale)
            )
            
            vocab_image = vocab_image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Position image using individual margins if available
            img_left = img_config.get('left_margin', img_config.get('x_offset', layout.safe_left))
            img_right = img_config.get('right_margin', layout.canvas_width - layout.safe_right)
            img_area_width = layout.canvas_width - img_left - img_right
            
            # Center image within its area
            img_x = img_left + (img_area_width - new_size[0]) // 2
            img_y = img_config['y_start'] + (img_config['height'] - new_size[1]) // 2
            
            # Paste with alpha channel
            canvas.paste(vocab_image, (img_x, img_y), vocab_image)
            
        except Exception as e:
            print(f"Warning: Could not load image: {e}")
    
    # ===========================================
    # DRAW BRANDING
    # ===========================================
    if layout.show_branding:
        # Use individual margins if available
        brand_left = brand_config.get('left_margin', brand_config.get('x_offset', layout.safe_left))
        brand_right = brand_config.get('right_margin', layout.canvas_width - layout.safe_right)
        brand_width = layout.canvas_width - brand_left - brand_right
        brand_center_x = brand_left + (brand_width // 2)
        
        draw_text_centered(
            draw=draw,
            text=layout.channel_name,
            y=brand_config['y_start'] + 5,
            font=font_branding,
            color=tuple(brand_config['color']),
            max_width=brand_width,
            center_x=brand_center_x
        )
    
    # Save frame
    if output_path is None:
        import config
        output_path = config.TEMP_DIR / "video_frame.png"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG")
    
    return output_path


def create_video_with_audio(frame_path: Path, audio_path: Path, output_path: Path,
                            duration: Optional[int] = None) -> Path:
    """
    Create video from static frame and audio using FFmpeg.
    
    Args:
        frame_path: Path to PNG frame
        audio_path: Path to MP3 audio
        output_path: Output video path
        duration: Video duration in seconds (None = use audio duration)
    
    Returns:
        Path to generated video
    """
    layout = get_layout_config()
    
    if duration is None:
        duration = layout.video_duration
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # FFmpeg command
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-loop", "1",  # Loop the image
        "-i", str(frame_path),  # Input image
        "-i", str(audio_path),  # Input audio
        "-c:v", "libx264",  # Video codec
        "-t", str(duration),  # Duration
        "-pix_fmt", "yuv420p",  # Pixel format for compatibility
        "-c:a", "aac",  # Audio codec
        "-b:a", "192k",  # Audio bitrate
        "-r", str(layout.video_fps),  # Frame rate
        "-shortest",  # End when shortest stream ends
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"FFmpeg failed: {result.stderr}")
    
    return output_path


def check_ffmpeg() -> bool:
    """Check if FFmpeg is installed."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False
