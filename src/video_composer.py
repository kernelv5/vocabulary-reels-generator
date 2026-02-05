# Video Composer Module
# Creates vocabulary videos using FFmpeg and Pillow
# Style: Minimalist educational Instagram Reels / YouTube Shorts
# STRICTLY following user specifications

import subprocess
import json
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import textwrap
import sys
sys.path.append(str(Path(__file__).parent.parent))
import config


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get font - Poppins/Sans style."""
    linux_fonts_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    linux_fonts_regular = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    
    windows_fonts_bold = ["C:/Windows/Fonts/arialbd.ttf"]
    windows_fonts_regular = ["C:/Windows/Fonts/arial.ttf"]
    
    font_list = (linux_fonts_bold + windows_fonts_bold) if bold else (linux_fonts_regular + windows_fonts_regular)
    
    for font_path in font_list:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()


def remove_background(image: Image.Image, threshold: int = 240) -> Image.Image:
    """Remove white/light background from image and make it transparent."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    data = image.getdata()
    new_data = []
    
    for item in data:
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    
    image.putdata(new_data)
    return image


def create_video_frame(word: str, definition: str, image_path: Optional[Path] = None,
                       output_path: Optional[Path] = None, show_word: bool = True,
                       show_definition: bool = True, show_image: bool = True) -> Path:
    """
    Create video frame with EXACT specifications:
    
    Canvas: 1080x1920 (9:16)
    Safe Area: 540px wide, centered (270px - 810px)
    
    Element Positioning (Y-axis from top):
    - Word Title: Start 175px, End 230px, Height 55px
    - Definition: Start 230px, End 305px, Height 75px  
    - Image: Start 305px, End 530px, Height 225px, Max Width 750px
    - Branding: Start 540px, End 570px, Height 30px
    """
    
    # Create canvas with pure white background
    canvas = Image.new("RGBA", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # Load fonts
    font_word = get_font(config.FONT_WORD_SIZE, bold=True)
    font_definition = get_font(config.FONT_DEFINITION_SIZE, bold=False)
    font_branding = get_font(config.FONT_BRANDING_SIZE, bold=False)
    
    # ===========================================
    # LAYOUT - EXACT specifications
    # ===========================================
    # Safe area boundaries
    safe_left = config.SAFE_AREA_LEFT      # 270px
    safe_right = config.SAFE_AREA_RIGHT    # 810px
    safe_width = config.SAFE_AREA_WIDTH    # 540px
    safe_center = config.VIDEO_WIDTH // 2  # 540px
    
    # Y positions from specifications
    y_word = config.LAYOUT_WORD_Y          # 175px
    y_definition = config.LAYOUT_DEF_Y     # 230px
    y_image = config.LAYOUT_IMAGE_Y        # 305px
    y_branding = config.LAYOUT_BRAND_Y     # 540px
    
    # ===========================================
    # DRAW WORD TITLE
    # Y: 175-230 (55px height), centered in safe area
    # ===========================================
    if show_word:
        word_display = word.capitalize()
        word_bbox = draw.textbbox((0, 0), word_display, font=font_word)
        word_width = word_bbox[2] - word_bbox[0]
        word_x = safe_center - (word_width // 2)
        draw.text((word_x, y_word), word_display, font=font_word, fill=config.WORD_COLOR)
    
    # ===========================================
    # DRAW DEFINITION
    # Y: 230-305 (75px height), centered in safe area
    # ===========================================
    if show_definition:
        # Calculate characters per line to fit in safe area
        max_chars_per_line = 28
        wrapped_lines = textwrap.wrap(definition, width=max_chars_per_line)
        
        # Line height to fit within 75px height for ~2-3 lines
        line_height = 28
        
        for i, line in enumerate(wrapped_lines):
            line_bbox = draw.textbbox((0, 0), line, font=font_definition)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = safe_center - (line_width // 2)
            line_y = y_definition + (i * line_height)
            draw.text((line_x, line_y), line, font=font_definition, fill=config.DEFINITION_COLOR)
    
    # ===========================================
    # DRAW IMAGE
    # Y: 305-530 (225px height), max 750px width, centered
    # ===========================================
    if show_image and image_path and Path(image_path).exists():
        try:
            vocab_image = Image.open(image_path)
            
            if vocab_image.mode != "RGBA":
                vocab_image = vocab_image.convert("RGBA")
            
            # Remove white background
            vocab_image = remove_background(vocab_image, threshold=235)
            
            # Resize to fit specifications: max 750px width, 225px height
            max_width = config.LAYOUT_IMAGE_MAX_WIDTH   # 750px
            max_height = config.LAYOUT_IMAGE_HEIGHT     # 225px
            
            ratio = min(max_width / vocab_image.width, max_height / vocab_image.height)
            new_width = int(vocab_image.width * ratio)
            new_height = int(vocab_image.height * ratio)
            
            vocab_image = vocab_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Center horizontally
            img_x = safe_center - (new_width // 2)
            
            # Center vertically within image area (305-530)
            image_area_center = y_image + (max_height // 2)
            img_y = image_area_center - (new_height // 2)
            
            # Paste with transparency
            canvas.paste(vocab_image, (img_x, img_y), vocab_image)
                
        except Exception as e:
            print(f"Warning: Could not load image {image_path}: {e}")
    
    # ===========================================
    # DRAW BRANDING
    # Y: 540-570 (30px height), centered in safe area
    # ===========================================
    brand_text = config.CHANNEL_NAME
    brand_bbox = draw.textbbox((0, 0), brand_text, font=font_branding)
    brand_width = brand_bbox[2] - brand_bbox[0]
    brand_x = safe_center - (brand_width // 2)
    draw.text((brand_x, y_branding), brand_text, font=font_branding, fill=config.DEFINITION_COLOR)
    
    # ===========================================
    # SAVE FRAME
    # ===========================================
    if output_path is None:
        output_path = config.TEMP_DIR / "frame.png"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert RGBA to RGB with white background
    rgb_canvas = Image.new("RGB", canvas.size, (255, 255, 255))
    rgb_canvas.paste(canvas, mask=canvas.split()[3] if canvas.mode == 'RGBA' else None)
    rgb_canvas.save(output_path, "PNG", quality=95)
    
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration using ffprobe."""
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 5.0


def create_video_with_audio(frame_path: Path, audio_path: Path, output_path: Path,
                            extra_duration: float = 1.5) -> Path:
    """Create video from static frame and audio using FFmpeg."""
    
    audio_duration = get_audio_duration(audio_path)
    total_duration = audio_duration + extra_duration
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(frame_path),
        "-i", str(audio_path),
        "-c:v", "libx264", 
        "-tune", "stillimage",
        "-c:a", "aac", 
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(total_duration),
        "-shortest",
        "-vf", f"scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg failed: {result.stderr}")
    
    return output_path


def check_ffmpeg() -> bool:
    """Check if FFmpeg is installed."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False
