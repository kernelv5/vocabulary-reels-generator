# Vocabulary Reels Generator - Configuration
# ============================================
# Style: STRICTLY matching inspiration image
# Minimalist educational Instagram Reels / YouTube Shorts

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
UPLOADS_DIR = BASE_DIR / "uploads"

# Create directories
for d in [OUTPUT_DIR, TEMP_DIR, UPLOADS_DIR]:
    d.mkdir(exist_ok=True)

# ===========================================
# DATA SOURCE - CSV File (Do not delete this file!)
# ===========================================
CSV_FILE = BASE_DIR / "csv_database_doNotTouch.csv"

COL_WORD = "word"
COL_DEFINITION = "definition"
COL_EXAMPLE = "example"
COL_PROMPT_IMAGE = "prompt_image_guideline"  # Custom prompt for image generation
COL_STATUS = "status"
COL_VIDEO_PATH = "video_path"

# ===========================================
# JSON2VIDEO API (Recommended for consistent design)
# Get your API key at: https://json2video.com/
# ===========================================
JSON2VIDEO_API_KEY = os.environ.get("JSON2VIDEO_API_KEY", "")
JSON2VIDEO_TEMPLATE_ID = os.environ.get("JSON2VIDEO_TEMPLATE_ID", "")  # Optional: pre-saved template
JSON2VIDEO_ENABLED = os.environ.get("JSON2VIDEO_ENABLED", "false").lower() == "true"

# ===========================================
# COMFYUI - Image Generation (for illustrations)
# ===========================================
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://host.docker.internal:8188")
COMFYUI_MODEL = os.environ.get("COMFYUI_MODEL", "DreamShaperXL_Lightning.safetensors")

IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024
IMAGE_STEPS = 4
IMAGE_CFG = 2.0

# Image prompt - Generate with WHITE background (will be removed to transparent)
# Uses {word} and {prompt_image_guideline} from CSV (falls back to definition if empty)
IMAGE_PROMPT_TEMPLATE = """Simple minimalist illustration showing the concept of "{word}": {prompt_image_guideline}. 
Style: Clean simple line drawing, muted brown and beige earth tones, 
simple cartoon characters or objects, solid pure white background, 
no text no letters no words, centered composition, flat illustration style, 
warm colors, educational clipart aesthetic, isolated on white."""

IMAGE_NEGATIVE_PROMPT = """text, words, letters, numbers, watermark, signature, 
complex background, gradient, pattern, dark background, colorful background,
photorealistic, 3d render, busy, cluttered, neon, vibrant colors"""

# ===========================================
# LOCAL TTS - Chatterbox TTS Server  
# ===========================================
TTS_URL = os.environ.get("TTS_URL", "http://host.docker.internal:8004/v1/audio/speech")
TTS_MODEL = os.environ.get("TTS_MODEL", "tts-1")
TTS_VOICE = os.environ.get("TTS_VOICE", "")
TTS_SPEED = float(os.environ.get("TTS_SPEED", "1.0"))

VOICE_SCRIPT_TEMPLATE = "{word}. {definition}."

# ===========================================
# VIDEO LAYOUT - Instagram Reels Specifications
# Canvas: 1080x1920 (9:16 aspect ratio)
# Safe Area: 540px wide, centered (270px - 810px)
# ===========================================
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_FORMAT = "mp4"
VIDEO_DURATION = 10  # seconds

# Element Y-positions (from your specifications)
LAYOUT_WORD_Y = 175        # Word title Y position
LAYOUT_WORD_HEIGHT = 55    # Word title height
LAYOUT_DEF_Y = 230         # Definition Y position  
LAYOUT_DEF_HEIGHT = 75     # Definition height
LAYOUT_IMAGE_Y = 305       # Image Y position
LAYOUT_IMAGE_HEIGHT = 225  # Image height
LAYOUT_IMAGE_MAX_WIDTH = 750
LAYOUT_BRAND_Y = 540       # Branding Y position
LAYOUT_BRAND_HEIGHT = 30   # Branding height

# Safe area (content centered within this)
SAFE_AREA_LEFT = 270
SAFE_AREA_RIGHT = 810
SAFE_AREA_WIDTH = 540

# ===========================================
# COLORS - Clean white minimalist
# ===========================================
BG_COLOR = (255, 255, 255)  # Pure white
WORD_COLOR = (35, 35, 35)   # Dark for title
DEFINITION_COLOR = (60, 60, 60)  # Gray for body

# ===========================================
# TYPOGRAPHY
# ===========================================
FONT_WORD_SIZE = 72        # Word title (was 85, adjusted for safe area)
FONT_DEFINITION_SIZE = 36  # Definition text
FONT_BRANDING_SIZE = 28    # Channel name

# ===========================================
# BRANDING
# ===========================================
CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "@WhiteEnglishVocabulary")

# ===========================================
# API SERVER SETTINGS
# ===========================================
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "5000"))
DEBUG = os.environ.get("FLASK_ENV", "production") != "production"
