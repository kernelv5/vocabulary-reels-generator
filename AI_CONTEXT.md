# 🤖 AI Assistant Context File

> **PURPOSE**: This file contains comprehensive project context for AI assistants (Claude, GPT, Copilot, etc.).
> When starting a new session or switching AI models, simply say:
> **"Read AI_CONTEXT.md and follow the instructions"**

---

## 📋 Quick Instructions for AI

1. **Read this entire file** before making any changes
2. **Check current branch**: `git branch` (currently on `version-3`)
3. **Understand the architecture**: Flask + Docker + ComfyUI + Chatterbox TTS
4. **Use VideoGeneratorV2** (not V1) - it reads from `layout_config.json`
5. **Test changes**: Rebuild container with `docker-compose up -d --build`

---

## 🎯 Project Overview

**Name**: Vocabulary Reels Generator  
**Purpose**: Generate YouTube Shorts / Instagram Reels style vocabulary videos  
**Tech Stack**: Python, Flask, Docker, FFmpeg, ComfyUI (Stable Diffusion), Chatterbox TTS

### Video Output Style
- **Format**: 9:16 vertical (1080x1920)
- **Duration**: 10 seconds
- **Style**: Minimalist, educational, white background
- **Content**: Word + Definition + AI-generated illustration + Voice

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Container                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Flask App (app.py)                   │    │
│  │  - Web UI at localhost:5000                          │    │
│  │  - REST API endpoints                                │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              VideoGeneratorV2                        │    │
│  │  - Reads layout_config.json                          │    │
│  │  - Orchestrates image + audio + video                │    │
│  └─────────────────────────────────────────────────────┘    │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌───────────┐      ┌───────────┐      ┌───────────────┐    │
│  │ ComfyUI   │      │ TTS       │      │ VideoComposer │    │
│  │ Client    │      │ Client    │      │ V2 (FFmpeg)   │    │
│  └───────────┘      └───────────┘      └───────────────┘    │
└─────────│───────────────────│───────────────────────────────┘
          │                   │
          ▼                   ▼
    ┌───────────┐      ┌───────────┐
    │ ComfyUI   │      │ Chatterbox│
    │ :8188     │      │ TTS :8004 │
    │ (Host)    │      │ (Host)    │
    └───────────┘      └───────────┘
```

---

## 📁 File Structure & Responsibilities

### Core Files (DO NOT DELETE)
| File | Purpose |
|------|---------|
| `app.py` | Main Flask application with Web UI and API |
| `config.py` | Configuration paths and environment variables |
| `layout_config.json` | Visual layout settings (edit via Layout Editor UI) |
| `docker-compose.yml` | Container orchestration |
| `Dockerfile` | Container build instructions |
| `csv_database_doNotTouch.csv` | Internal word database (auto-managed by app) |

### Source Files (`src/`)
| File | Purpose |
|------|---------|
| `generator_v2.py` | **Main generator** - uses layout_config.json |
| `video_composer_v2.py` | FFmpeg video creation with per-element margins |
| `image_generator_advanced.py` | ComfyUI image generation (supports use_layout_size) |
| `preview_generator.py` | Layout preview image generation |
| `comfyui_client.py` | ComfyUI API wrapper |
| `tts_client.py` | Chatterbox TTS API wrapper |
| `csv_reader.py` | CSV file handling utilities |
| `layout_config.py` | Layout configuration loader |
| `layout_editor_routes.py` | Layout editor API endpoints |

### Legacy Files (Keep for reference)
| File | Purpose |
|------|---------|
| `generator.py` | V1 generator (uses hardcoded config.py) |
| `video_composer.py` | V1 video composer |
| `json2video_client.py` | JSON2Video API client (unused) |

---

## 🔧 Key Technical Details

### Layout Configuration (`layout_config.json`)
```json
{
  "elements": {
    "word_title": { "y_start": 500, "y_end": 650, "left_margin": 270, "right_margin": 270 },
    "definition": { "y_start": 689, "y_end": 789, "left_margin": 180, "right_margin": 180 },
    "image": { "y_start": 900, "y_end": 1400, "max_width": 750, "height": 500 },
    "branding": { "y_start": 1450, "y_end": 1480 }
  },
  "image_generation": {
    "use_layout_size": false,  // When true, uses image element dimensions
    "width": 1024,
    "height": 1024
  }
}
```

### Docker Volume Mounts
- `./output:/app/output` - Generated videos persist here
- `./uploads:/app/uploads` - Uploaded images
- `./csv_database_doNotTouch.csv:/app/csv_database_doNotTouch.csv` - Word database

### Important: V1 vs V2
- **ALWAYS use V2 classes**: `VideoGeneratorV2`, `VideoComposerV2`
- V2 reads all settings from `layout_config.json`
- V1 uses hardcoded values from `config.py` (deprecated)

---

## 🌿 Git Branches

| Branch | Purpose |
|--------|---------|
| `master` | Original stable release |
| `feature/layout-editor-enhancements` | Added per-element margins |
| `version-3` | **CURRENT** - Latest with all features |

### Version-3 Features
- ✅ Per-element left/right margins
- ✅ Layout-based image sizing option
- ✅ Batch progress bar
- ✅ Individual video download buttons
- ✅ Clear vocabulary list button
- ✅ Clear output folder button

---

## 📡 External Services

### ComfyUI (Image Generation)
- **URL**: `http://127.0.0.1:8188` (host) → `http://host.docker.internal:8188` (container)
- **Model**: DreamShaperXL_Lightning.safetensors
- **Sampler**: euler_ancestral, 4 steps, CFG 2

### Chatterbox TTS (Voice)
- **URL**: `http://localhost:8004` (host) → `http://host.docker.internal:8004` (container)
- **Endpoint**: `/v1/audio/speech`
- **Format**: MP3 output

---

## 🔄 Common Operations

### Rebuild Container
```bash
docker-compose down
docker-compose up -d --build
```

### Rebuild Without Cache
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Check Container Logs
```bash
docker-compose logs -f
```

### Enter Container Shell
```bash
docker exec -it vocab-reels-generator bash
```

---

## ⚠️ Known Issues & Solutions

### Issue: Layout changes not reflecting in video
**Cause**: Using V1 generator instead of V2  
**Solution**: Ensure `app.py` imports `VideoGeneratorV2` from `src.generator_v2`

### Issue: vocabulary.csv is a directory
**Cause**: Docker volume mount creates directory if file doesn't exist  
**Solution**: Delete directory, create file with headers, restart container

### Issue: CSV import "Expected 3 fields, saw X"
**Cause**: Commas in definition text  
**Solution**: Remove commas from definitions or quote fields properly

### Issue: Container can't reach ComfyUI/TTS
**Cause**: Services not running or wrong URL  
**Solution**: Check services are running on host, verify `host.docker.internal` URLs

---

## 📝 Code Patterns

### Adding a New API Endpoint
```python
# In app.py
@app.route('/api/new-endpoint', methods=['POST'])
def new_endpoint():
    data = request.get_json()
    # Process data
    return jsonify({'status': 'success'})
```

### Modifying Layout Elements
1. Edit `layout_config.json` directly, OR
2. Use Layout Editor UI at http://localhost:5000 (Layout Editor tab)

### Adding UI Button (in app.py HTML_TEMPLATE)
```javascript
// In the JavaScript section
async function newAction() {
    const res = await fetch('/api/endpoint', { method: 'POST' });
    const data = await res.json();
    // Handle response
}
```

---

## 🎨 Current Layout Configuration (Theme1)

```
┌─────────────────────────────────┐ 0px
│                                 │
│                                 │
│           WORD TITLE            │ 500-650px
│        (72px, bold, center)     │
│                                 │
│          Definition             │ 689-789px
│    (36px, normal, center)       │
│                                 │
│                                 │
│      ┌─────────────────┐        │ 900px
│      │                 │        │
│      │   AI Generated  │        │
│      │   Illustration  │        │
│      │   (750x500px)   │        │
│      │                 │        │
│      └─────────────────┘        │ 1400px
│                                 │
│    @WhiteEnglishVocabulary      │ 1450-1480px
│                                 │
└─────────────────────────────────┘ 1920px
```

---

## 🚀 Future Enhancement Ideas

1. **Multiple themes**: Support different layout templates
2. **Font upload**: Custom fonts via UI
3. **Animation presets**: Text animation options
4. **Batch scheduling**: Queue videos for generation
5. **Cloud storage**: Upload to S3/GCS
6. **Social posting**: Direct upload to YouTube/Instagram

---

## 📞 Project Metadata

- **Owner**: User (kernelv5+github@gmail.com)
- **Repository**: vocabulary-reels-generator
- **Current Branch**: version-3
- **Container Name**: vocab-reels-generator
- **Port**: 5000

---

## ✅ Checklist for AI Assistants

Before making changes:
- [ ] Read this entire context file
- [ ] Check current git branch (`git branch`)
- [ ] Understand which files need modification
- [ ] Use V2 classes (not V1)
- [ ] Test with `docker-compose up -d --build`
- [ ] Verify changes at http://localhost:5000

After making changes:
- [ ] Ensure no syntax errors
- [ ] Rebuild container if needed
- [ ] Test the feature works
- [ ] Update this context file if architecture changes

---

*Last Updated: February 6, 2026*
