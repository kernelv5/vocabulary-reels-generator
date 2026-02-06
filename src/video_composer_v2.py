"""
Video Composer Module - Updated to use layout_config.json
Creates vocabulary videos with exact layout specifications
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
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


def draw_text_with_bold_word(draw: ImageDraw.Draw, text: str, word: str, y: int,
                             font: ImageFont.FreeTypeFont, bold_font: ImageFont.FreeTypeFont,
                             color: tuple, max_width: int, center_x: int,
                             line_spacing: float = 1.2) -> int:
    """Draw text centered with the word emphasized in bold and slightly larger size."""
    if not text:
        return y

    word_lower = word.lower()
    tokens = re.split(r'(\s+)', text)

    def token_font(token: str) -> ImageFont.FreeTypeFont:
        if token.isspace():
            return font
        normalized = re.sub(r'[^A-Za-z0-9]+', '', token).lower()
        return bold_font if normalized == word_lower and normalized else font

    def token_width(token: str) -> int:
        token_bbox = draw.textbbox((0, 0), token, font=token_font(token))
        return token_bbox[2] - token_bbox[0]

    base_height = draw.textbbox((0, 0), "Ag", font=font)[3]
    bold_height = draw.textbbox((0, 0), "Ag", font=bold_font)[3]
    line_height = int(max(base_height, bold_height) * line_spacing)

    lines = []
    current_line = []
    current_width = 0

    for token in tokens:
        width = token_width(token)
        if current_line and current_width + width > max_width:
            lines.append(current_line)
            current_line = [token]
            current_width = width
        else:
            current_line.append(token)
            current_width += width

    if current_line:
        lines.append(current_line)

    current_y = y
    for line_tokens in lines:
        line_width = sum(token_width(token) for token in line_tokens)
        x = center_x - (line_width // 2)
        for token in line_tokens:
            draw.text((x, current_y), token, font=token_font(token), fill=color)
            x += token_width(token)
        current_y += line_height

    return current_y


def create_video_frame(word: str, definition: str, example: str = "",
                       output_path: Optional[Path] = None) -> Path:
    """
    Create video frame following layout_config.json specifications.
    
    Args:
        word: Vocabulary word
        definition: Word definition
        example: Example sentence
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
    example_config = layout.example
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

    example_font_size = example_config['font_size']
    bold_example_font_size = example_font_size + 2
    font_example = get_font(example_font_size, bold=(example_config['font_weight'] == 'bold'))
    font_example_bold = get_font(bold_example_font_size, bold=True)
    
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
    # DRAW EXAMPLE
    # ===========================================
    example_left = example_config.get('left_margin', layout.safe_left)
    example_right = example_config.get('right_margin', layout.canvas_width - layout.safe_right)
    example_width = layout.canvas_width - example_left - example_right
    example_center_x = example_left + (example_width // 2)
    example_text = example or ""

    draw_text_with_bold_word(
        draw=draw,
        text=example_text,
        word=word,
        y=example_config['y_start'] + 5,
        font=font_example,
        bold_font=font_example_bold,
        color=tuple(example_config['color']),
        max_width=example_width - 40,
        center_x=example_center_x,
        line_spacing=example_config.get('line_spacing', 1.2)
    )
    
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


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration using ffprobe."""
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 10.0  # Default fallback


def create_video_with_audio(frame_path: Path, audio_path: Path, output_path: Path,
                            duration: Optional[int] = None,
                            extra_seconds: float = 1.5) -> Path:
    """
    Create video from static frame and audio using FFmpeg.
    
    Args:
        frame_path: Path to PNG frame
        audio_path: Path to MP3 audio
        output_path: Output video path
        duration: Video duration in seconds (None = use audio duration + extra_seconds)
        extra_seconds: Extra seconds to add after audio ends (default 3.0)
    
    Returns:
        Path to generated video
    """
    layout = get_layout_config()
    
    if duration is None:
        # Calculate duration from audio + extra time
        audio_duration = get_audio_duration(audio_path)
        duration = int(audio_duration + extra_seconds)
        print(f"  Audio duration: {audio_duration:.1f}s + {extra_seconds}s extra = {duration}s video")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # FFmpeg command - removed -shortest to allow video to extend beyond audio
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-loop", "1",  # Loop the image
        "-i", str(frame_path),  # Input image
        "-i", str(audio_path),  # Input audio
        "-c:v", "libx264",  # Video codec
        "-t", str(duration),  # Duration (audio + extra)
        "-pix_fmt", "yuv420p",  # Pixel format for compatibility
        "-c:a", "aac",  # Audio codec
        "-b:a", "192k",  # Audio bitrate
        "-r", str(layout.video_fps),  # Frame rate
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
