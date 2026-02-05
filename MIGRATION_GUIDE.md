# Migration Guide: V1 to V2

## 🎯 Overview

This guide helps you transition from the current implementation to V2 with new features while maintaining your existing videos and workflows.

## ⚡ TL;DR - Quick Migration

```bash
cd C:\Users\admin\Documents\Claude-Document\vocabulary-reels-generator

# Backup current data
cp vocabulary.csv vocabulary_backup.csv

# Rebuild with V2
docker-compose down
docker-compose up -d --build

# Test V2 features
docker exec -it vocabulary-reels-generator python test_v2_features.py

# Done! Both V1 and V2 work now
```

## 📋 Detailed Migration Steps

### Step 1: Backup Current Data

```bash
# Backup vocabulary database
cp vocabulary.csv vocabulary_backup.csv

# Backup any custom config (if you modified)
cp config.py config_backup.py

# Backup generated videos (optional, if space limited)
# tar -czf output_backup.tar.gz output/
```

### Step 2: Stop Current Container

```bash
docker-compose down
```

### Step 3: Update Code (Already Done!)

All V2 files have been created:
- ✅ `layout_config.json`
- ✅ `src/layout_config.py`
- ✅ `src/preview_generator.py`
- ✅ `src/image_generator_advanced.py`
- ✅ `src/video_composer_v2.py`
- ✅ `src/generator_v2.py`
- ✅ Updated `app.py` with new endpoints
- ✅ Updated `requirements.txt` with rembg

### Step 4: Rebuild Container

```bash
docker-compose up -d --build
```

This will:
- Install new dependencies (rembg for background removal)
- Load new Python modules
- Keep all your existing data

### Step 5: Verify Services

```bash
# Check services are running
docker-compose ps

# Check logs
docker-compose logs -f app

# Test API
curl http://localhost:5000/api/health
```

### Step 6: Test V2 Features

```bash
# Run test suite
docker exec -it vocabulary-reels-generator python test_v2_features.py

# Generate a preview
curl -X POST http://localhost:5000/api/preview/layout \
  -H "Content-Type: application/json" \
  -d '{"show_guides": true}'

# Check output
open http://localhost:5000/output/layout_preview.png
```

### Step 7: Test Video Generation

Generate a test video to ensure everything works:

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Migration",
    "definition": "Moving from one version to another",
    "example": "The V2 migration was smooth and easy"
  }'
```

Or use the web UI at `http://localhost:5000`

## 🔄 What Changed & What Didn't

### ✅ Still Works (No Changes Needed)

- **Web UI**: Same interface, new features added
- **API Endpoints**: All existing endpoints work
- **CSV Format**: Same format, no changes
- **Docker Setup**: Same docker-compose.yml
- **Generated Videos**: Existing videos still accessible
- **Workflow**: Can still use same n8n workflows

### 🆕 New Features Available

- **Layout Configuration**: Edit `layout_config.json`
- **Preview System**: `/api/preview/layout` endpoint
- **Advanced Image Gen**: `/api/image/generate` with parameters
- **Background Removal**: Automatic transparency
- **Better Fonts**: Canva Sans with fallbacks

### 📝 Optional Improvements

You can now:

1. **Fine-tune layout** without touching code
2. **Test designs** before generating videos
3. **Control image quality** with seeds and steps
4. **Get transparent backgrounds** automatically

But you don't have to use these - V1 workflow still works!

## 🎨 Customizing Your Layout

### Current Layout (V1)
Your videos use hardcoded values from `config.py`

### New Layout (V2)
Edit `layout_config.json` to adjust:

```json
{
  "elements": {
    "word_title": {
      "y_start": 175,    // Move this
      "font_size": 72,   // Adjust this
      "color": [35, 35, 35]  // Change this
    }
  }
}
```

Then reload:
```bash
curl -X POST http://localhost:5000/api/layout/config/reload
```

## 🖼️ Using Advanced Image Generation

### Old Way (V1)
```bash
curl -X POST http://localhost:5000/api/generate/image \
  -H "Content-Type: application/json" \
  -d '{"word": "Test", "definition": "..."}'
```

Random seed, fixed settings, white background remains.

### New Way (V2)
```bash
curl -X POST http://localhost:5000/api/image/generate \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Test",
    "definition": "...",
    "seed": 42,
    "steps": 8,
    "cfg_scale": 2.5,
    "remove_background": true
  }'
```

Controlled seed, quality settings, transparent background!

## 🔧 Configuration Migration

### If You Customized config.py

Your custom values from `config.py` can be moved to `layout_config.json`:

**Example:** You changed word position in config.py:
```python
# config.py (old)
LAYOUT_WORD_Y = 180  # Changed from 175
```

Move to layout_config.json:
```json
{
  "elements": {
    "word_title": {
      "y_start": 180
    }
  }
}
```

Then reload config via API.

### If You Modified Prompts

**Old**: Changed `IMAGE_PROMPT_TEMPLATE` in config.py

**New**: Edit in layout_config.json:
```json
{
  "image_generation": {
    "prompt_template": "Your custom prompt with {word} and {definition}"
  }
}
```

## 📊 Comparing V1 and V2

| Feature | V1 | V2 |
|---------|----|----|
| Video generation | ✅ | ✅ |
| Layout customization | Code changes required | JSON config |
| Preview system | ❌ | ✅ Visual previews |
| Image parameters | Fixed | Fully customizable |
| Background removal | Manual | Automatic |
| Font options | Limited | Canva Sans + fallbacks |
| Testing | Generate video to test | Quick preview |
| Configuration | Hardcoded | JSON-based |

## 🚀 Recommended Workflow

### For Testing New Designs

1. Edit `layout_config.json`
2. Generate preview with guides
3. Adjust if needed
4. Test with one video
5. Batch generate when satisfied

### For Production

1. Keep using existing workflow (V1 still works)
2. Gradually adopt V2 features as needed
3. Use image generation parameters for better results
4. Use preview system for new vocabulary sets

## ⚠️ Known Issues & Solutions

### Issue: Fonts Don't Look Right

**Solution**: Install Canva Sans or use fallbacks
```bash
# Check available fonts
docker exec vocabulary-reels-generator fc-list | grep -i sans

# Edit layout_config.json to use available font
{
  "typography": {
    "font_family": "DejaVu Sans",
    "fallback_fonts": ["Arial"]
  }
}
```

### Issue: Background Not Transparent

**Solution**: Ensure rembg installed
```bash
# Check installation
docker exec vocabulary-reels-generator pip list | grep rembg

# If missing, rebuild
docker-compose down
docker-compose up -d --build
```

### Issue: Preview Not Generating

**Solution**: Check logs and permissions
```bash
# Check logs
docker-compose logs app | tail -50

# Test directly
docker exec vocabulary-reels-generator python -c "from src.preview_generator import create_preview; print(create_preview())"
```

### Issue: Old Videos Look Different from New

**Solution**: This is expected! V2 has:
- Better background removal
- Improved fonts
- Exact positioning

To match old style, you can:
1. Copy old config values to layout_config.json
2. Disable background removal
3. Use same image seeds

## 🎯 Next Steps

After migration:

1. ✅ **Test video generation** - Ensure basics work
2. ✅ **Generate preview** - See new design with guides
3. ✅ **Try custom seeds** - Find better images
4. ✅ **Adjust layout** - Fine-tune positioning
5. ✅ **Batch generate** - Create multiple videos

## 📚 Documentation Reference

- **QUICKSTART_V2.md** - Step-by-step usage
- **README_V2.md** - Complete feature documentation
- **V2_SUMMARY.md** - Overview of changes
- **test_v2_features.py** - Code examples

## 💡 Pro Tips

1. **Use preview system liberally** - It's fast and helps avoid surprises
2. **Save good seeds** - When you find a good image, note the seed
3. **Backup layout configs** - Create multiple configs for different styles
4. **Test incrementally** - Don't change everything at once
5. **Keep V1 workflows** - Until you're comfortable with V2

## 🆘 Rollback Plan

If you need to rollback:

```bash
# Stop V2
docker-compose down

# Restore backup
cp config_backup.py config.py
cp vocabulary_backup.csv vocabulary.csv

# Remove V2 files (optional)
rm layout_config.json
rm src/*_v2.py
rm src/layout_config.py
rm src/preview_generator.py
rm src/image_generator_advanced.py

# Rebuild V1
docker-compose up -d --build
```

But honestly, V2 is backward compatible, so rollback shouldn't be needed!

## ✅ Migration Checklist

Before considering migration complete:

- [ ] Container rebuilt successfully
- [ ] All services show "Connected" in web UI
- [ ] Test video generated successfully
- [ ] Preview system works
- [ ] Layout configuration loads
- [ ] Advanced image generation works (if ComfyUI available)
- [ ] Existing CSV vocabulary still loads
- [ ] Old videos still accessible

## 🎉 You're Done!

Your system now has:
- ✅ JSON-based configuration
- ✅ Visual preview system
- ✅ Advanced image generation
- ✅ Automatic background removal
- ✅ Better font handling
- ✅ Exact layout control

And your old workflows still work!

For questions or issues:
```bash
docker-compose logs -f
```

Happy video generating! 🚀
