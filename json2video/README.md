# JSON2Video Integration for Vocabulary Reels
# =============================================

## Overview

This folder contains JSON2Video templates and integration code for creating 
consistent vocabulary reels using the JSON2Video API.

## Why JSON2Video?

| Feature | Local (FFmpeg) | JSON2Video |
|---------|----------------|------------|
| Design Consistency | Manual | ✅ Template-based |
| Font Support | System fonts only | ✅ Google Fonts + Custom |
| Text Animation | Limited | ✅ Built-in animations |
| Voice Generation | Requires local TTS | ✅ Built-in AI voices |
| Scalability | Single machine | ✅ Cloud rendering |
| n8n Integration | Custom API | ✅ Native support |

## Setup

### 1. Get JSON2Video API Key

1. Go to https://json2video.com/
2. Sign up for an account
3. Get your API key from the dashboard

### 2. Create Template (Optional but Recommended)

1. Go to JSON2Video Dashboard → Movie Templates
2. Click "Add new template"
3. Copy the contents of `vocabulary_reel_template.json`
4. Save and note the Template ID

### 3. Configure Environment

Add to your `.env` file or docker-compose.yml:

```bash
JSON2VIDEO_API_KEY=your_api_key_here
JSON2VIDEO_TEMPLATE_ID=your_template_id_here  # Optional
JSON2VIDEO_ENABLED=true
```

## Template Specifications

### Canvas
- **Width:** 1080px
- **Height:** 1920px (9:16 aspect ratio)
- **Duration:** 10 seconds
- **FPS:** 30

### Safe Area
- **Width:** 540px
- **Left boundary:** 270px
- **Right boundary:** 810px

### Element Positioning (Y-axis)

| Element | Start | End | Height |
|---------|-------|-----|--------|
| Word Title | 175px | 230px | 55px |
| Definition | 230px | 305px | 75px |
| Image | 305px | 530px | 225px |
| Branding | 540px | 570px | 30px |

### Typography

| Element | Font | Size | Weight | Color |
|---------|------|------|--------|-------|
| Word | Poppins | 72px | 700 | #232323 |
| Definition | Poppins | 32px | 400 | #3C3C3C |
| Branding | Poppins | 28px | 500 | #3C3C3C |

### Voice
- **Voice:** en-US-AriaNeural
- **Speed:** 0.9
- **Start:** 0.5s delay

## Usage

### Using Template ID (Recommended)

```python
from src.json2video_client import JSON2VideoClient

client = JSON2VideoClient(api_key="your_key")

result = client.create_vocabulary_reel_with_template(
    template_id="your_template_id",
    word="Disband",
    definition="To break up or stop working together as a group.",
    image_url="https://your-cdn.com/disband.png",
    channel_name="@WhiteEnglishVocabulary"
)

# Wait for rendering
final = client.wait_for_completion(result["project"])
print(f"Video URL: {final['video_url']}")
```

### Using Direct JSON

```python
result = client.create_vocabulary_reel(
    word="Disband",
    definition="To break up or stop working together as a group.",
    image_url="https://your-cdn.com/disband.png"
)
```

### API Endpoint

```bash
POST /api/generate/json2video
Content-Type: application/json

{
    "word": "Disband",
    "definition": "To break up or stop working together as a group.",
    "image_url": "https://your-cdn.com/disband.png"
}
```

## n8n Integration

### Webhook → JSON2Video Workflow

```
[Webhook Trigger]
       ↓
[HTTP Request - Generate Image with ComfyUI]
       ↓
[Upload Image to CDN/S3]
       ↓
[HTTP Request - JSON2Video]
  POST https://api.json2video.com/v2/movies
  Headers: x-api-key: {{$credentials.json2video}}
  Body: {
    "template": "YOUR_TEMPLATE_ID",
    "variables": {
      "word": "{{$json.word}}",
      "definition": "{{$json.definition}}",
      "image_url": "{{$json.image_url}}",
      "channel_name": "@WhiteEnglishVocabulary"
    }
  }
       ↓
[Wait 30s]
       ↓
[HTTP Request - Check Status]
  GET https://api.json2video.com/v2/movies?project={{$json.project}}
       ↓
[Download Video / Upload to YouTube]
```

## Files

- `vocabulary_reel_template.json` - Main template for JSON2Video
- `template_vocabulary_reel.json` - Alternative template with variables
- `../src/json2video_client.py` - Python client for JSON2Video API

## Pricing

JSON2Video has usage-based pricing:
- Free tier: Limited renders/month
- Pay-as-you-go: ~$0.05-0.10 per video minute

Check https://json2video.com/pricing for current rates.
