# Vocabulary Reels Generator V2

## 🎯 New Features

### ✅ JSON-Based Layout Configuration
- All layout measurements stored in `layout_config.json`
- Easy to adjust positions, colors, fonts, and spacing
- No need to edit code to change design

### ✅ Preview & Apply System
- Generate layout previews before creating videos
- Test different configurations visually
- Apply changes instantly

### ✅ Advanced Image Generation
- Customizable parameters: seed, steps, CFG scale
- Custom prompts and negative prompts
- Automatic background removal for transparency
- Control image quality and style

### ✅ Design Consistency
- ✓ Clean white background
- ✓ Transparent image backgrounds (background removed automatically)
- ✓ Canva Sans font (with fallbacks: Inter, Open Sans, Arial)
- ✓ Precise layout following your specifications

## 📐 Layout Specifications

```
Canvas: 1080 x 1920 (9:16 aspect ratio)
Safe Area: 540px wide (270px - 810px)

Element Positions (Y-axis from top):
┌─────────────────────────────────┐  0px
│                                 │
│     ┌───────────────────┐       │  
│     │    Disband        │       │  175px ─┐ Word Title (55px)
│     │                   │       │  230px ─┘
│     │  To break up or   │       │         │ Definition (75px)
│     │  stop working...  │       │  305px ─┘
│     │                   │       │         │
│     │   ┌─────────┐     │       │         │ Image (225px)
│     │   │ [IMAGE] │     │       │         │ Max 750px width
│     │   └─────────┘     │       │  530px ─┘
│     │                   │       │  540px ─┐
│     │@WhiteEnglishVocab │       │         │ Branding (30px)
│     │                   │       │  570px ─┘
│     └───────────────────┘       │
│      ↑                 ↑        │
│    270px             810px      │
│         Safe Area (540px)       │
└─────────────────────────────────┘  1920px
```

## 🚀 Quick Start

### 1. Start Services

```bash
docker-compose down
docker-compose up -d --build
docker-compose logs -f
```

### 2. Access Web UI

Open browser: `http://localhost:5000`

## 🔧 Configuration

### Edit Layout Configuration

The layout is controlled by `layout_config.json`:

```json
{
  "canvas": {
    "width": 1080,
    "height": 1920,
    "background_color": [255, 255, 255]
  },
  "elements": {
    "word_title": {
      "y_start": 175,
      "y_end": 230,
      "font_size": 72,
      "color": [35, 35, 35]
    },
    ...
  }
}
```

### Ways to Update Configuration

**Option 1: Edit JSON file directly**
```bash
# Edit layout_config.json
nano layout_config.json

# Reload configuration via API
curl -X POST http://localhost:5000/api/layout/config/reload
```

**Option 2: Via API**
```bash
curl -X POST http://localhost:5000/api/layout/config \
  -H "Content-Type: application/json" \
  -d '{"elements": {"word_title": {"y_start": 180}}}'
```

**Option 3: Via Python**
```python
from src.layout_config import get_layout_config

layout = get_layout_config()
layout.update_element('word_title', {'y_start': 180})
layout.save()
```

## 🎨 Preview System

### Generate Layout Preview

**Via API:**
```bash
curl -X POST http://localhost:5000/api/preview/layout \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Serendipity",
    "definition": "Finding something good by happy chance",
    "show_guides": true
  }'
```

**Via Python:**
```python
from src.preview_generator import create_preview

preview_path = create_preview(
    word="Disband",
    definition="To break up or stop working together as a group",
    show_guides=True  # Shows guide lines
)
```

Preview will be saved to `temp/layout_preview.png` and shows:
- Safe area boundaries (purple lines)
- Element boundaries with Y positions
- Sample text in correct positions
- Image placeholder

## 🖼️ Advanced Image Generation

### Generate Image with Custom Parameters

**Via API:**
```bash
curl -X POST http://localhost:5000/api/image/generate \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Serendipity",
    "definition": "Finding something good by happy chance",
    "seed": 42,
    "steps": 8,
    "cfg_scale": 3.0,
    "remove_background": true
  }'
```

**Available Parameters:**
- `seed` - Random seed (-1 for random, any number for reproducible results)
- `steps` - Diffusion steps (default: 4, more = better quality but slower)
- `cfg_scale` - How closely to follow prompt (default: 2.0, range 1-10)
- `width` / `height` - Image dimensions (default: 1024x1024)
- `sampler` - Sampling method (default: "euler_ancestral")
- `custom_prompt` - Override default prompt template
- `custom_negative` - Override default negative prompt
- `remove_background` - Remove white background for transparency (default: true)

**Via Python:**
```python
from src.image_generator_advanced import generate_vocab_image_advanced

result = generate_vocab_image_advanced(
    word="Ephemeral",
    definition="Lasting for a very short time",
    output_path=Path("output/ephemeral.png"),
    seed=12345,
    steps=8,
    cfg_scale=2.5,
    remove_background=True
)

if result['success']:
    print(f"Image saved: {result['image_path']}")
    print(f"Seed used: {result['seed']}")
```

## 📋 API Endpoints

### Layout Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/layout/config` | GET | Get current layout configuration |
| `/api/layout/config` | POST | Update layout configuration |
| `/api/layout/config/reload` | POST | Reload configuration from file |

### Preview & Testing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/preview/layout` | POST | Generate layout preview with guides |

### Advanced Image Generation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/image/generate` | POST | Generate image with custom parameters |

### Video Generation (Existing)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate` | POST | Generate complete video |
| `/api/generate/image` | POST | Generate image only (preview) |
| `/api/generate/audio` | POST | Generate audio only (preview) |

## 🛠️ Development Workflow

### 1. Test Layout Changes

```bash
# 1. Edit layout_config.json
nano layout_config.json

# 2. Generate preview to check
curl -X POST http://localhost:5000/api/preview/layout \
  -H "Content-Type: application/json" \
  -d '{"show_guides": true}' \
  > /dev/null && open output/layout_preview.png

# 3. If good, generate a test video
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Test",
    "definition": "Testing the new layout"
  }'
```

### 2. Test Image Generation

```bash
# Generate with different seeds to find best result
for seed in 42 123 456 789 1000; do
  curl -X POST http://localhost:5000/api/image/generate \
    -H "Content-Type: application/json" \
    -d "{
      \"word\": \"Ephemeral\",
      \"definition\": \"Lasting for a very short time\",
      \"seed\": $seed,
      \"steps\": 6
    }"
done
```

### 3. Compare Configurations

```bash
# Save current config
curl http://localhost:5000/api/layout/config > config_backup.json

# Test new config
curl -X POST http://localhost:5000/api/layout/config \
  -H "Content-Type: application/json" \
  -d @new_config.json

# Preview
curl -X POST http://localhost:5000/api/preview/layout

# Restore if needed
curl -X POST http://localhost:5000/api/layout/config \
  -H "Content-Type: application/json" \
  -d @config_backup.json
```

## 📦 Project Structure

```
vocabulary-reels-generator/
├── layout_config.json          # ← Layout configuration (NEW)
├── app.py                      # Main Flask application
├── config.py                   # Legacy config (for compatibility)
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Docker setup
│
├── src/
│   ├── layout_config.py        # ← Layout config manager (NEW)
│   ├── preview_generator.py   # ← Preview system (NEW)
│   ├── image_generator_advanced.py  # ← Advanced image gen (NEW)
│   ├── video_composer_v2.py   # ← Updated video composer (NEW)
│   ├── generator_v2.py         # ← Updated generator (NEW)
│   │
│   ├── generator.py            # Original generator (still works)
│   ├── video_composer.py       # Original composer (still works)
│   ├── comfyui_client.py       # ComfyUI integration
│   ├── tts_client.py           # TTS integration
│   └── csv_reader.py           # CSV handling
│
├── output/                     # Generated videos
├── temp/                       # Temporary files
└── uploads/                    # User uploads
```

## 🎯 Design Specifications Met

✅ **Clear white background** - Pure white (#FFFFFF) canvas
✅ **Transparent image background** - Automatic background removal using rembg
✅ **Canva Sans font** - With fallback chain (Inter → Open Sans → Arial)
✅ **Exact positioning** - All elements at specified Y coordinates
✅ **Safe area compliance** - 540px centered safe area (270-810px)
✅ **JSON configuration** - All settings in layout_config.json
✅ **Preview system** - Test before generating
✅ **Image customization** - Seed, steps, CFG, prompts

## 🔍 Troubleshooting

### Preview shows wrong fonts
```bash
# Check available fonts
fc-list | grep -i "inter\|sans\|arial"

# Install missing fonts (Ubuntu/Debian)
sudo apt-get install fonts-inter fonts-open-sans

# Docker: rebuild container
docker-compose down
docker-compose up -d --build
```

### Background not transparent
```bash
# Check if rembg is installed
pip list | grep rembg

# Install if missing
pip install rembg==2.0.57

# Docker: rebuild
docker-compose down
docker-compose up -d --build
```

### Layout doesn't update
```bash
# Reload configuration
curl -X POST http://localhost:5000/api/layout/config/reload

# Or restart container
docker-compose restart
```

## 📝 Notes

- Layout config changes are immediate after reload
- Preview generation is fast (no video encoding)
- Image generation respects layout config settings
- V1 and V2 systems can coexist (V1 for backward compatibility)
- All measurements in pixels for precision

## 🎓 Examples

See `examples/` folder for:
- Sample layout configurations
- Image generation scripts
- Batch processing workflows
- Custom prompt templates

---

For questions or issues, check the logs:
```bash
docker-compose logs -f
```
