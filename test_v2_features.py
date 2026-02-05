#!/usr/bin/env python3
"""
Test Script for V2 Features
Demonstrates layout preview, config management, and advanced image generation
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import json
from src.layout_config import get_layout_config
from src.preview_generator import create_preview
from src.image_generator_advanced import generate_vocab_image_advanced
import config


def test_layout_config():
    """Test layout configuration loading and manipulation."""
    print("\n" + "="*60)
    print("TEST 1: Layout Configuration")
    print("="*60)
    
    layout = get_layout_config()
    
    print(f"\n📐 Canvas Size: {layout.canvas_width} x {layout.canvas_height}")
    print(f"🎨 Background: RGB{layout.background_color}")
    print(f"📝 Font Family: {layout.font_family}")
    print(f"🔤 Fallback Fonts: {', '.join(layout.fallback_fonts)}")
    
    print(f"\n📍 Safe Area:")
    print(f"   Left: {layout.safe_left}px")
    print(f"   Right: {layout.safe_right}px")
    print(f"   Width: {layout.safe_width}px")
    print(f"   Center X: {layout.safe_center_x}px")
    
    print(f"\n📦 Elements:")
    for elem_name in ['word_title', 'definition', 'image', 'branding']:
        elem = layout.get_element(elem_name)
        print(f"   {elem_name}:")
        print(f"      Y: {elem['y_start']}-{elem['y_end']}px (height: {elem['height']}px)")
        if 'font_size' in elem:
            print(f"      Font: {elem['font_size']}px, {elem['font_weight']}")
        if 'color' in elem:
            print(f"      Color: RGB{tuple(elem['color'])}")
    
    print(f"\n🖼️  Image Generation:")
    print(f"   Size: {layout.image_width} x {layout.image_height}")
    print(f"   Steps: {layout.image_steps}")
    print(f"   CFG Scale: {layout.image_cfg_scale}")
    print(f"   Background Removal: {layout.background_removal_enabled}")
    
    print("\n✅ Configuration loaded successfully!")
    

def test_preview_generation():
    """Test preview generation with guide lines."""
    print("\n" + "="*60)
    print("TEST 2: Preview Generation")
    print("="*60)
    
    test_cases = [
        {
            "word": "Serendipity",
            "definition": "Finding something good by happy chance or accident",
        },
        {
            "word": "Ephemeral",
            "definition": "Lasting for a very short time; fleeting",
        },
        {
            "word": "Mellifluous",
            "definition": "Sweet or musical; pleasant to hear",
        }
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n📸 Generating preview {i+1}: {test['word']}")
        
        preview_path = create_preview(
            word=test['word'],
            definition=test['definition'],
            output_path=config.TEMP_DIR / f"preview_{i+1}_{test['word'].lower()}.png",
            show_guides=True
        )
        
        print(f"   ✓ Saved: {preview_path}")
    
    print("\n✅ All previews generated successfully!")


def test_image_generation():
    """Test advanced image generation with different parameters."""
    print("\n" + "="*60)
    print("TEST 3: Advanced Image Generation")
    print("="*60)
    
    word = "Tranquility"
    definition = "A state of peace and calm"
    
    # Test 1: Default settings
    print(f"\n🎨 Test 1: Default settings")
    result1 = generate_vocab_image_advanced(
        word=word,
        definition=definition,
        output_path=config.OUTPUT_DIR / "test_tranquility_default.png"
    )
    
    if result1['success']:
        print(f"   ✓ Generated: {result1['image_path']}")
        print(f"   Seed: {result1['seed']}")
    else:
        print(f"   ✗ Failed: {result1['error']}")
    
    # Test 2: Custom seed
    print(f"\n🎨 Test 2: Custom seed (reproducible)")
    result2 = generate_vocab_image_advanced(
        word=word,
        definition=definition,
        output_path=config.OUTPUT_DIR / "test_tranquility_seed42.png",
        seed=42,
        steps=6
    )
    
    if result2['success']:
        print(f"   ✓ Generated: {result2['image_path']}")
        print(f"   Seed: {result2['seed']}")
    else:
        print(f"   ✗ Failed: {result2['error']}")
    
    # Test 3: High quality
    print(f"\n🎨 Test 3: High quality (more steps)")
    result3 = generate_vocab_image_advanced(
        word=word,
        definition=definition,
        output_path=config.OUTPUT_DIR / "test_tranquility_highquality.png",
        seed=42,  # Same seed for comparison
        steps=12,
        cfg_scale=3.0
    )
    
    if result3['success']:
        print(f"   ✓ Generated: {result3['image_path']}")
        print(f"   Steps: {result3['steps']}, CFG: {result3['cfg_scale']}")
    else:
        print(f"   ✗ Failed: {result3['error']}")
    
    # Test 4: No background removal
    print(f"\n🎨 Test 4: Without background removal")
    result4 = generate_vocab_image_advanced(
        word=word,
        definition=definition,
        output_path=config.OUTPUT_DIR / "test_tranquility_no_bg_removal.png",
        seed=42,
        remove_background=False
    )
    
    if result4['success']:
        print(f"   ✓ Generated: {result4['image_path']}")
        print(f"   Background Removed: {result4['background_removed']}")
    else:
        print(f"   ✗ Failed: {result4['error']}")
    
    print("\n✅ Image generation tests completed!")


def test_config_modification():
    """Test modifying and saving configuration."""
    print("\n" + "="*60)
    print("TEST 4: Configuration Modification")
    print("="*60)
    
    layout = get_layout_config()
    
    # Backup current config
    original_config = layout.to_dict()
    print("\n💾 Backed up original configuration")
    
    # Modify word title position
    print("\n📝 Modifying word title Y position...")
    layout.update_element('word_title', {'y_start': 200})
    
    print(f"   Original: {original_config['elements']['word_title']['y_start']}px")
    print(f"   Modified: {layout.word_title['y_start']}px")
    
    # Test preview with modified config
    print("\n📸 Generating preview with modified config...")
    preview_path = create_preview(
        word="Modified",
        definition="This preview uses the modified configuration",
        output_path=config.TEMP_DIR / "preview_modified.png",
        show_guides=True
    )
    print(f"   ✓ Saved: {preview_path}")
    
    # Restore original config
    print("\n♻️  Restoring original configuration...")
    layout.save(original_config)
    layout.reload()
    print(f"   ✓ Restored: {layout.word_title['y_start']}px")
    
    print("\n✅ Configuration modification test completed!")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 VOCABULARY REELS GENERATOR V2 - TEST SUITE")
    print("="*60)
    
    try:
        # Test 1: Configuration
        test_layout_config()
        
        # Test 2: Preview Generation
        test_preview_generation()
        
        # Test 3: Image Generation (requires ComfyUI)
        from src.image_generator_advanced import AdvancedImageGenerator
        generator = AdvancedImageGenerator()
        
        if generator.is_server_running():
            test_image_generation()
        else:
            print("\n⚠️  Skipping image generation tests (ComfyUI not running)")
            print(f"   Start ComfyUI at: {generator.comfyui_url}")
        
        # Test 4: Config Modification
        test_config_modification()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED!")
        print("="*60)
        print("\n📂 Check output files in:")
        print(f"   Previews: {config.TEMP_DIR}")
        print(f"   Images: {config.OUTPUT_DIR}")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
