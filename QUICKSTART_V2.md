# Quick Start Guide - V2 Features

## 🚀 Setup

### 1. Rebuild Container with New Dependencies

```bash
cd C:\Users\admin\Documents\Claude-Document\vocabulary-reels-generator

# Stop current container
docker-compose down

# Rebuild with new dependencies (includes rembg)
docker-compose up -d --build

# Watch logs
docker-compose logs -f
```

### 2. Verify Services

Open browser: `http://localhost:5000`

Check service status on the dashboard:
- ✅ ComfyUI (Image AI) - should be "Connected"
- ✅ TTS Server (Voice AI) - should be "Connected"  
- ✅ FFmpeg (Video) - should be "Installed"

## 🎨 Using New Features

### A. Preview Layout Before Generating

**Method 1: Via Python Script**
```bash
# Inside container
docker exec -it vocabulary-reels-generator python test_v2_features.py
```

**Method 2: Via API (from host)**
```bash
curl -X POST http://localhost:5000/api/preview/layout \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Disband",
    "definition": "To break up or stop working together as a group",
    "show_guides": true
  }'
```

Preview will be saved to `/output/` and you can view it at:
`http://localhost:5000/output/layout_preview.png`

### B. Adjust Layout Configuration

**Option 1: Edit JSON File**

1. Edit `layout_config.json` on your host machine
2. Reload via API:
```bash
curl -X POST http://localhost:5000/api/layout/config/reload
```

**Option 2: Via API**

```bash
# Example: Move word title down by 10px
curl -X POST http://localhost:5000/api/layout/config \
  -H "Content-Type: application/json" \
  -d '{
    "elements": {
      "word_title": {
        "y_start": 185,
        "y_end": 240
      }
    }
  }'
```

**Option 3: Via Web UI (Coming Soon)**
A visual editor will be added to the web interface.

### C. Generate Image with Custom Parameters

**Example: Generate with specific seed**

```bash
curl -X POST http://localhost:5000/api/image/generate \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Ephemeral",
    "definition": "Lasting for a very short time",
    "seed": 42,
    "steps": 8,
    "cfg_scale": 2.5,
    "remove_background": true
  }'
```

**Response:**
```json
{
  "success": true,
  "image_path": "/app/output/ephemeral_image_20260205_123456.png",
  "seed": 42,
  "steps": 8,
  "cfg_scale": 2.5,
  "background_removed": true,
  "image_url": "/output/ephemeral_image_20260205_123456.png"
}
```

View at: `http://localhost:5000/output/ephemeral_image_20260205_123456.png`

## 📋 Complete Workflow Example

### Step 1: Test Layout with Preview

```bash
# Generate preview with your word
curl -X POST http://localhost:5000/api/preview/layout \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Serendipity",
    "definition": "Finding something good by happy chance or accident",
    "show_guides": true
  }'
```

Open: `http://localhost:5000/output/layout_preview.png`

### Step 2: Adjust Layout if Needed

If elements don't look right, edit `layout_config.json`:

```json
{
  "elements": {
    "word_title": {
      "y_start": 180,  // Move down 5px
      "font_size": 68  // Slightly smaller
    }
  }
}
```

Reload and preview again:
```bash
curl -X POST http://localhost:5000/api/layout/config/reload
curl -X POST http://localhost:5000/api/preview/layout ...
```

### Step 3: Test Image Generation

```bash
# Try different seeds to find best image
curl -X POST http://localhost:5000/api/image/generate \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Serendipity",
    "definition": "Finding something good by happy chance or accident",
    "seed": 123,
    "steps": 6
  }'
```

Check output folder for generated images.

### Step 4: Generate Final Video

Once happy with layout and image style:

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Serendipity",
    "definition": "Finding something good by happy chance or accident",
    "example": "Meeting her was pure serendipity"
  }'
```

Or use the web UI form!

## 🎯 Tips & Tricks

### Finding the Right Seed

Different seeds produce different images. To find the best:

```bash
#!/bin/bash
# Generate 5 versions with different seeds
for seed in 42 123 456 789 1000; do
  echo "Testing seed: $seed"
  curl -X POST http://localhost:5000/api/image/generate \
    -H "Content-Type: application/json" \
    -d "{
      \"word\": \"Tranquility\",
      \"definition\": \"A state of peace and calm\",
      \"seed\": $seed,
      \"steps\": 6
    }"
done
```

Then browse `http://localhost:5000/output/` to pick the best one!

### Layout Guides

Always use `show_guides: true` in previews to see:
- Safe area boundaries (purple lines)
- Element position markers
- Y-position labels

This helps ensure text fits properly.

### Background Removal

If images have leftover white pixels:

1. Try lowering the threshold in `layout_config.json`:
```json
{
  "image_generation": {
    "background_removal": {
      "enabled": true,
      "threshold": 235
    }
  }
}
```

2. Or disable auto-removal and use custom images with transparency:
```json
{
  "image_generation": {
    "background_removal": {
      "enabled": false
    }
  }
}
```

### Font Issues

If fonts don't look right:

1. Check available fonts in container:
```bash
docker exec -it vocabulary-reels-generator fc-list | grep -i "sans"
```

2. Update fallback fonts in `layout_config.json`:
```json
{
  "typography": {
    "font_family": "Canva Sans",
    "fallback_fonts": ["Inter", "Helvetica", "Arial"]
  }
}
```

## 📊 Monitoring

### Check Service Status

```bash
curl http://localhost:5000/api/status | json_pp
```

### View Logs

```bash
# All services
docker-compose logs -f

# Just app
docker-compose logs -f app

# Last 50 lines
docker-compose logs --tail=50
```

### List Generated Files

```bash
curl http://localhost:5000/api/files | json_pp
```

## 🐛 Troubleshooting

### Preview Not Generating

```bash
# Check Python can access layout config
docker exec -it vocabulary-reels-generator python -c "from src.layout_config import get_layout_config; print(get_layout_config().canvas_width)"

# Should print: 1080
```

### Images Not Transparent

```bash
# Check if rembg installed
docker exec -it vocabulary-reels-generator pip list | grep rembg

# Should show: rembg 2.0.57 (or similar)

# If not, rebuild container
docker-compose down
docker-compose up -d --build
```

### Layout Not Updating

```bash
# Force reload
curl -X POST http://localhost:5000/api/layout/config/reload

# Or restart container
docker-compose restart app
```

### ComfyUI Not Connecting

Check ComfyUI is running and accessible:
```bash
curl http://host.docker.internal:8188/system_stats
```

If not, start ComfyUI on host machine.

## 📚 Next Steps

1. ✅ Test preview generation
2. ✅ Experiment with different seeds
3. ✅ Fine-tune layout positions
4. ✅ Generate batch of videos
5. ✅ Set up automation (n8n workflow)

For detailed API documentation, see `README_V2.md`

---

**Need Help?**
- Check logs: `docker-compose logs -f`
- Test services: `http://localhost:5000/api/status`
- Run test suite: `docker exec -it vocabulary-reels-generator python test_v2_features.py`
