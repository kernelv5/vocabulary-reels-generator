"""
Layout Editor Routes - Add to app.py
"""

LAYOUT_EDITOR_ROUTES = '''
# ============================================
# LAYOUT EDITOR UI
# ============================================

@app.route('/editor')
def layout_editor():
    """Serve the layout editor interface."""
    return render_template_string(LAYOUT_EDITOR_HTML)


@app.route('/api/fonts/list', methods=['GET'])
def api_list_fonts():
    """List all available fonts (system + uploaded)."""
    fonts = []
    
    # System fonts
    import subprocess
    try:
        result = subprocess.run(['fc-list', ':'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\\n'):
                if ':' in line:
                    font_path = line.split(':')[0]
                    font_name = Path(font_path).stem
                    fonts.append({
                        "name": font_name,
                        "path": font_path,
                        "type": "system"
                    })
    except Exception as e:
        print(f"Error listing system fonts: {e}")
    
    # Uploaded fonts
    fonts_dir = config.BASE_DIR / "fonts"
    if fonts_dir.exists():
        for font_file in fonts_dir.glob("*.ttf"):
            fonts.append({
                "name": font_file.stem,
                "path": str(font_file),
                "type": "uploaded"
            })
        for font_file in fonts_dir.glob("*.otf"):
            fonts.append({
                "name": font_file.stem,
                "path": str(font_file),
                "type": "uploaded"
            })
    
    return jsonify(fonts)


@app.route('/api/fonts/upload', methods=['POST'])
def api_upload_font():
    """Upload a custom font file."""
    if 'font_file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['font_file']
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    # Check file extension
    allowed_extensions = {'.ttf', '.otf', '.woff', '.woff2'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        return jsonify({"error": f"Invalid font format. Allowed: {', '.join(allowed_extensions)}"}), 400
    
    # Create fonts directory
    fonts_dir = config.BASE_DIR / "fonts"
    fonts_dir.mkdir(exist_ok=True)
    
    # Save font file
    filename = secure_filename(file.filename)
    filepath = fonts_dir / filename
    file.save(filepath)
    
    return jsonify({
        "success": True,
        "filename": filename,
        "path": str(filepath),
        "message": f"Font '{filename}' uploaded successfully"
    })


@app.route('/api/fonts/google', methods=['GET'])
def api_list_google_fonts():
    """List popular Google Fonts."""
    # Popular fonts that work well for videos
    google_fonts = [
        {"name": "Inter", "category": "sans-serif", "weights": ["400", "500", "600", "700", "800"]},
        {"name": "Poppins", "category": "sans-serif", "weights": ["400", "500", "600", "700", "800"]},
        {"name": "Roboto", "category": "sans-serif", "weights": ["400", "500", "700", "900"]},
        {"name": "Open Sans", "category": "sans-serif", "weights": ["400", "600", "700", "800"]},
        {"name": "Montserrat", "category": "sans-serif", "weights": ["400", "500", "600", "700", "800"]},
        {"name": "Lato", "category": "sans-serif", "weights": ["400", "700", "900"]},
        {"name": "Raleway", "category": "sans-serif", "weights": ["400", "500", "600", "700", "800"]},
        {"name": "Nunito", "category": "sans-serif", "weights": ["400", "600", "700", "800"]},
        {"name": "Ubuntu", "category": "sans-serif", "weights": ["400", "500", "700"]},
        {"name": "Work Sans", "category": "sans-serif", "weights": ["400", "500", "600", "700", "800"]},
    ]
    
    return jsonify(google_fonts)


@app.route('/api/preview/download', methods=['POST'])
def api_download_preview():
    """Generate and download preview image."""
    from src.preview_generator import create_preview
    
    data = request.get_json() or {}
    word = data.get('word', 'Preview')
    definition = data.get('definition', 'This is a preview of your layout configuration')
    show_guides = data.get('show_guides', False)
    
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"preview_{timestamp}.png"
        
        preview_path = create_preview(
            word=word,
            definition=definition,
            output_path=output_path,
            show_guides=show_guides
        )
        
        return send_file(preview_path, as_attachment=True, download_name=f"layout_preview_{timestamp}.png")
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''
