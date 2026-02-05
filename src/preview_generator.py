"""
Layout Preview System - Generate preview images to test layout configuration
"""

from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.layout_config import get_layout_config

def find_font(font_name: str, size: int, fallbacks: list = None) -> ImageFont.FreeTypeFont:
    """
    Try to load a font by name, falling back to alternatives.
    
    Args:
        font_name: Primary font name
        size: Font size
        fallbacks: List of fallback font names
    
    Returns:
        ImageFont object
    """
    font_paths_to_try = []
    
    # Common font locations
    font_locations = [
        Path("/usr/share/fonts"),
        Path("/System/Library/Fonts"),
        Path("C:/Windows/Fonts"),
        Path.home() / ".fonts",
    ]
    
    # Build list of fonts to try
    fonts_to_try = [font_name]
    if fallbacks:
        fonts_to_try.extend(fallbacks)
    fonts_to_try.append("Arial")  # Final fallback
    
    # Search for fonts
    for font in fonts_to_try:
        for location in font_locations:
            if location.exists():
                # Try variations
                variations = [
                    f"{font}.ttf",
                    f"{font.lower()}.ttf",
                    f"{font.replace(' ', '')}.ttf",
                    f"{font.replace(' ', '-')}.ttf",
                    f"{font}Bold.ttf",
                ]
                
                for var in variations:
                    for font_file in location.rglob(var):
                        try:
                            return ImageFont.truetype(str(font_file), size)
                        except:
                            continue
    
    # Ultimate fallback
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()


def draw_text_centered(draw: ImageDraw.Draw, text: str, y: int, 
                       font: ImageFont.FreeTypeFont, color: tuple, 
                       max_width: int, center_x: int):
    """
    Draw text centered at given Y position.
    
    Args:
        draw: ImageDraw object
        text: Text to draw
        y: Y position (top)
        font: Font to use
        color: RGB color tuple
        max_width: Maximum width for text
        center_x: X coordinate of center
    """
    # Get text bbox
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # If text too wide, wrap it
    if text_width > max_width:
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
        line_height = text_height * 1.2
        total_height = len(lines) * line_height
        current_y = y
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x = center_x - (line_width // 2)
            draw.text((x, current_y), line, font=font, fill=color)
            current_y += line_height
    else:
        # Draw single line
        x = center_x - (text_width // 2)
        draw.text((x, y), text, font=font, fill=color)


def create_preview(word: str = "Disband", 
                   definition: str = "To break up or stop working together as a group",
                   output_path: Optional[Path] = None,
                   show_guides: bool = True) -> Path:
    """
    Create a preview image showing the layout with sample text.
    
    Args:
        word: Sample word to display
        definition: Sample definition to display
        output_path: Where to save preview. If None, saves to temp.
        show_guides: Whether to show guide lines
    
    Returns:
        Path to generated preview image
    """
    layout = get_layout_config()
    
    # Create canvas
    img = Image.new('RGB', layout.canvas_size, layout.background_color)
    draw = ImageDraw.Draw(img)
    
    # Draw guides if requested
    if show_guides:
        guide_color = (200, 180, 255, 100)  # Light purple
        
        # Safe area boundaries
        draw.line([(layout.safe_left, 0), (layout.safe_left, layout.canvas_height)], 
                 fill=guide_color, width=2)
        draw.line([(layout.safe_right, 0), (layout.safe_right, layout.canvas_height)], 
                 fill=guide_color, width=2)
        
        # Element boundaries
        elements = ['word_title', 'definition', 'image', 'branding']
        for elem_name in elements:
            elem = layout.get_element(elem_name)
            y_start = elem['y_start']
            y_end = elem['y_end']
            
            # Horizontal lines
            draw.line([(0, y_start), (layout.canvas_width, y_start)], 
                     fill=guide_color, width=1)
            draw.line([(0, y_end), (layout.canvas_width, y_end)], 
                     fill=guide_color, width=1)
            
            # Label
            label_font = ImageFont.load_default()
            draw.text((10, y_start + 5), f"{elem_name} ({y_start}px)", 
                     fill=(150, 150, 150), font=label_font)
    
    # Get fonts
    word_font = find_font(
        layout.font_family, 
        layout.word_title['font_size'],
        layout.fallback_fonts
    )
    
    def_font = find_font(
        layout.font_family,
        layout.definition['font_size'],
        layout.fallback_fonts
    )
    
    brand_font = find_font(
        layout.font_family,
        layout.branding['font_size'],
        layout.fallback_fonts
    )
    
    # Draw word title - use individual margins if available
    word_elem = layout.word_title
    word_left = word_elem.get('left_margin', layout.safe_left)
    word_right = word_elem.get('right_margin', layout.canvas_width - layout.safe_right)
    word_width = layout.canvas_width - word_left - word_right
    word_center_x = word_left + (word_width // 2)
    
    draw_text_centered(
        draw, word,
        layout.word_title['y_start'] + 10,
        word_font,
        layout.get_color_rgb('word_title'),
        word_width,
        word_center_x
    )
    
    # Draw definition - use individual margins if available
    def_elem = layout.definition
    def_left = def_elem.get('left_margin', layout.safe_left)
    def_right = def_elem.get('right_margin', layout.canvas_width - layout.safe_right)
    def_width = layout.canvas_width - def_left - def_right
    def_center_x = def_left + (def_width // 2)
    
    draw_text_centered(
        draw, definition,
        layout.definition['y_start'] + 10,
        def_font,
        layout.get_color_rgb('definition'),
        def_width - 40,  # Slight padding
        def_center_x
    )
    
    # Draw placeholder for image - use individual margins if available
    img_elem = layout.image
    img_left = img_elem.get('left_margin', img_elem.get('x_offset', layout.safe_left))
    img_right = img_elem.get('right_margin', layout.canvas_width - layout.safe_right)
    img_area_width = layout.canvas_width - img_left - img_right
    img_center_x = img_left + (img_area_width // 2)
    img_center_y = (img_elem['y_start'] + img_elem['y_end']) // 2
    placeholder_size = 180
    
    draw.rectangle([
        img_center_x - placeholder_size//2,
        img_center_y - placeholder_size//2,
        img_center_x + placeholder_size//2,
        img_center_y + placeholder_size//2
    ], fill=(240, 230, 220), outline=(200, 180, 160), width=3)
    
    # Draw "[IMAGE]" text in placeholder
    placeholder_font = find_font(layout.font_family, 36, layout.fallback_fonts)
    draw.text(
        (img_center_x - 60, img_center_y - 20),
        "[IMAGE]",
        font=placeholder_font,
        fill=(150, 140, 130)
    )
    
    # Draw branding - use individual margins if available
    if layout.show_branding:
        brand_elem = layout.branding
        brand_left = brand_elem.get('left_margin', brand_elem.get('x_offset', layout.safe_left))
        brand_right = brand_elem.get('right_margin', layout.canvas_width - layout.safe_right)
        brand_width = layout.canvas_width - brand_left - brand_right
        brand_center_x = brand_left + (brand_width // 2)
        
        draw_text_centered(
            draw, layout.channel_name,
            layout.branding['y_start'] + 5,
            brand_font,
            layout.get_color_rgb('branding'),
            brand_width,
            brand_center_x
        )
    
    # Save
    if output_path is None:
        import config
        output_path = config.TEMP_DIR / "layout_preview.png"
    
    img.save(output_path, 'PNG')
    print(f"✓ Preview saved: {output_path}")
    
    return output_path


if __name__ == "__main__":
    # Test preview generation
    preview_path = create_preview(
        word="Serendipity",
        definition="Finding something good by happy chance or accident",
        show_guides=True
    )
    print(f"Preview created: {preview_path}")
