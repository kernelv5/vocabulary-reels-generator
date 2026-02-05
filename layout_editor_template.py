# Layout Editor HTML Template
# Add this to app.py after HTML_TEMPLATE

LAYOUT_EDITOR_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Layout Editor - Vocabulary Reels</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 24px; }
        .tab-btn { padding: 12px 24px; border-radius: 8px; font-weight: 600; transition: all 0.3s; }
        .tab-btn.active { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .tab-btn:not(.active) { background: #e5e7eb; color: #4b5563; }
        .tab-btn:not(.active):hover { background: #d1d5db; }
        .slider-container { position: relative; padding-top: 24px; }
        .slider-value { position: absolute; top: 0; left: 0; background: #667eea; color: white; padding: 4px 12px; border-radius: 6px; font-size: 14px; font-weight: bold; }
        .preview-box { width: 360px; height: 640px; background: white; margin: 0 auto; position: relative; box-shadow: 0 20px 60px rgba(0,0,0,0.3); border-radius: 24px; overflow: hidden; border: 8px solid #333; }
        .guide-line { position: absolute; width: 100%; height: 2px; background: rgba(102, 126, 234, 0.5); pointer-events: none; z-index: 10; }
        .guide-vertical { position: absolute; width: 2px; height: 100%; background: rgba(102, 126, 234, 0.5); pointer-events: none; z-index: 10; }
        .guide-label { position: absolute; background: rgba(102, 126, 234, 0.9); color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; z-index: 11; }
        .color-btn { width: 50px; height: 50px; border-radius: 10px; border: 3px solid #e5e7eb; cursor: pointer; transition: all 0.2s; }
        .color-btn:hover { transform: scale(1.05); border-color: #667eea; }
        .font-item { padding: 16px; border: 2px solid #e5e7eb; border-radius: 12px; cursor: pointer; transition: all 0.2s; }
        .font-item:hover { border-color: #667eea; background: #f9fafb; }
        .font-item.selected { border-color: #667eea; background: #eef2ff; border-width: 3px; }
        .toast { position: fixed; bottom: 30px; right: 30px; background: #10b981; color: white; padding: 16px 24px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); z-index: 1000; display: none; }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <header class="gradient-bg text-white py-6 shadow-lg">
        <div class="container mx-auto px-6">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                    <a href="/" class="hover:text-purple-200 transition"><i class="fas fa-arrow-left text-xl"></i></a>
                    <div>
                        <h1 class="text-3xl font-bold">Layout Editor</h1>
                        <p class="text-purple-200 text-sm mt-1">Configure, preview & customize your videos</p>
                    </div>
                </div>
                <div class="flex gap-3">
                    <button onclick="loadConfig()" class="bg-white/20 hover:bg-white/30 px-5 py-2 rounded-lg transition">
                        <i class="fas fa-sync-alt mr-2"></i>Reload
                    </button>
                    <button onclick="downloadConfig()" class="bg-white/20 hover:bg-white/30 px-5 py-2 rounded-lg transition">
                        <i class="fas fa-download mr-2"></i>Export
                    </button>
                </div>
            </div>
        </div>
    </header>

    <main class="container mx-auto px-6 py-8">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Controls -->
            <div class="lg:col-span-2 space-y-6">
                <!-- Tabs -->
                <div class="flex flex-wrap gap-2">
                    <button onclick="switchTab('layout')" id="tab-layout" class="tab-btn active">
                        <i class="fas fa-ruler-combined mr-2"></i>Layout
                    </button>
                    <button onclick="switchTab('colors')" id="tab-colors" class="tab-btn">
                        <i class="fas fa-palette mr-2"></i>Colors
                    </button>
                    <button onclick="switchTab('fonts')" id="tab-fonts" class="tab-btn">
                        <i class="fas fa-font mr-2"></i>Fonts
                    </button>
                </div>

                <!-- Layout Tab -->
                <div id="content-layout" class="card space-y-6">
                    <h2 class="text-2xl font-bold">Element Positioning</h2>
                    
                    <!-- Word Title -->
                    <div class="border-l-4 border-purple-500 pl-4">
                        <h3 class="font-semibold mb-3">Word Title</h3>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="slider-container">
                                <div class="slider-value" id="word-y-val">175px</div>
                                <label class="block text-sm font-medium mb-2">Y Position</label>
                                <input type="range" id="word-y" min="50" max="400" value="175" class="w-full" oninput="updateSlider('word-y')">
                            </div>
                            <div class="slider-container">
                                <div class="slider-value" id="word-size-val">72px</div>
                                <label class="block text-sm font-medium mb-2">Font Size</label>
                                <input type="range" id="word-size" min="40" max="120" value="72" class="w-full" oninput="updateSlider('word-size')">
                            </div>
                        </div>
                    </div>

                    <!-- Definition -->
                    <div class="border-l-4 border-blue-500 pl-4">
                        <h3 class="font-semibold mb-3">Definition</h3>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="slider-container">
                                <div class="slider-value" id="def-y-val">230px</div>
                                <label class="block text-sm font-medium mb-2">Y Position</label>
                                <input type="range" id="def-y" min="100" max="500" value="230" class="w-full" oninput="updateSlider('def-y')">
                            </div>
                            <div class="slider-container">
                                <div class="slider-value" id="def-size-val">36px</div>
                                <label class="block text-sm font-medium mb-2">Font Size</label>
                                <input type="range" id="def-size" min="20" max="60" value="36" class="w-full" oninput="updateSlider('def-size')">
                            </div>
                        </div>
                    </div>

                    <!-- Image -->
                    <div class="border-l-4 border-green-500 pl-4">
                        <h3 class="font-semibold mb-3">Image</h3>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="slider-container">
                                <div class="slider-value" id="img-y-val">305px</div>
                                <label class="block text-sm font-medium mb-2">Y Position</label>
                                <input type="range" id="img-y" min="200" max="600" value="305" class="w-full" oninput="updateSlider('img-y')">
                            </div>
                            <div class="slider-container">
                                <div class="slider-value" id="img-h-val">225px</div>
                                <label class="block text-sm font-medium mb-2">Height</label>
                                <input type="range" id="img-h" min="100" max="400" value="225" class="w-full" oninput="updateSlider('img-h')">
                            </div>
                        </div>
                    </div>

                    <!-- Branding -->
                    <div class="border-l-4 border-yellow-500 pl-4">
                        <h3 class="font-semibold mb-3">Branding</h3>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="slider-container">
                                <div class="slider-value" id="brand-y-val">540px</div>
                                <label class="block text-sm font-medium mb-2">Y Position</label>
                                <input type="range" id="brand-y" min="400" max="700" value="540" class="w-full" oninput="updateSlider('brand-y')">
                            </div>
                            <div class="slider-container">
                                <div class="slider-value" id="brand-size-val">28px</div>
                                <label class="block text-sm font-medium mb-2">Font Size</label>
                                <input type="range" id="brand-size" min="16" max="48" value="28" class="w-full" oninput="updateSlider('brand-size')">
                            </div>
                        </div>
                        <div class="mt-4">
                            <label class="block text-sm font-medium mb-2">Channel Name</label>
                            <input type="text" id="channel-name" value="@WhiteEnglishVocabulary" 
                                   class="w-full px-4 py-2 border-2 rounded-lg" oninput="updatePreview()">
                        </div>
                    </div>
                </div>

                <!-- Colors Tab -->
                <div id="content-colors" class="card space-y-6 hidden">
                    <h2 class="text-2xl font-bold">Color Palette</h2>
                    <div class="grid grid-cols-2 gap-6">
                        <div>
                            <label class="block text-sm font-semibold mb-2">Background</label>
                            <input type="color" id="bg-color" value="#ffffff" onchange="updatePreview()" class="color-btn">
                        </div>
                        <div>
                            <label class="block text-sm font-semibold mb-2">Word Title</label>
                            <input type="color" id="word-color" value="#232323" onchange="updatePreview()" class="color-btn">
                        </div>
                        <div>
                            <label class="block text-sm font-semibold mb-2">Definition</label>
                            <input type="color" id="def-color" value="#3c3c3c" onchange="updatePreview()" class="color-btn">
                        </div>
                        <div>
                            <label class="block text-sm font-semibold mb-2">Branding</label>
                            <input type="color" id="brand-color" value="#646464" onchange="updatePreview()" class="color-btn">
                        </div>
                    </div>
                    
                    <div class="pt-4">
                        <h3 class="font-semibold mb-3">Quick Themes</h3>
                        <div class="flex flex-wrap gap-3">
                            <button onclick="applyTheme('default')" class="px-4 py-2 border-2 rounded-lg hover:border-purple-500">🤍 Clean</button>
                            <button onclick="applyTheme('dark')" class="px-4 py-2 bg-gray-800 text-white rounded-lg">🖤 Dark</button>
                            <button onclick="applyTheme('blue')" class="px-4 py-2 bg-blue-50 border-2 border-blue-300 rounded-lg">💙 Blue</button>
                        </div>
                    </div>
                </div>

                <!-- Fonts Tab -->
                <div id="content-fonts" class="card space-y-6 hidden">
                    <h2 class="text-2xl font-bold flex items-center gap-2">
                        <i class="fab fa-google text-blue-500"></i>Google Fonts
                    </h2>
                    <div id="fonts-list" class="grid grid-cols-2 gap-4">
                        <p class="col-span-2 text-center text-gray-500">Loading fonts...</p>
                    </div>
                    
                    <div class="pt-6 border-t">
                        <h3 class="font-semibold mb-3">Upload Custom Font</h3>
                        <input type="file" id="font-upload" accept=".ttf,.otf" onchange="uploadFont()" 
                               class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100">
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="flex gap-3">
                    <button onclick="saveConfig()" class="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-green-700 hover:to-emerald-700 transition">
                        <i class="fas fa-check mr-2"></i>Save & Apply
                    </button>
                    <button onclick="downloadPreview()" class="bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 transition">
                        <i class="fas fa-download mr-2"></i>Download Preview
                    </button>
                </div>
            </div>

            <!-- Preview -->
            <div class="lg:col-span-1">
                <div class="card sticky top-6">
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-xl font-bold">Live Preview</h2>
                        <button onclick="toggleGuides()" id="guides-btn" class="px-3 py-1 bg-purple-100 text-purple-700 rounded-lg text-sm">
                            <i class="fas fa-ruler"></i> Guides
                        </button>
                    </div>
                    
                    <div class="space-y-3 mb-4">
                        <input type="text" id="preview-word" value="Serendipity" placeholder="Word" 
                               class="w-full px-3 py-2 border-2 rounded-lg text-sm" oninput="updatePreview()">
                        <textarea id="preview-def" rows="2" placeholder="Definition" 
                                  class="w-full px-3 py-2 border-2 rounded-lg text-sm" 
                                  oninput="updatePreview()">Finding something good by happy chance</textarea>
                    </div>

                    <div id="preview-box" class="preview-box"></div>
                    
                    <p class="mt-4 text-center text-sm text-gray-500">Scale: 1:3 (360x640 → 1080x1920)</p>
                </div>
            </div>
        </div>
    </main>

    <div id="toast" class="toast">
        <div class="flex items-center gap-3">
            <i class="fas fa-check-circle text-2xl"></i>
            <div>
                <p class="font-semibold">Success!</p>
                <p class="text-sm" id="toast-msg"></p>
            </div>
        </div>
    </div>

    <script>
        let config = null;
        let showGuides = true;

        window.addEventListener('DOMContentLoaded', () => {
            loadConfig();
            loadFonts();
            updatePreview();
        });

        function switchTab(tab) {
            ['layout', 'colors', 'fonts'].forEach(t => {
                document.getElementById(`tab-${t}`).classList.toggle('active', t === tab);
                document.getElementById(`content-${t}`).classList.toggle('hidden', t !== tab);
            });
            if (tab === 'fonts') loadFonts();
        }

        async function loadConfig() {
            const res = await fetch('/api/layout/config');
            config = await res.json();
            
            document.getElementById('word-y').value = config.elements.word_title.y_start;
            document.getElementById('word-size').value = config.elements.word_title.font_size;
            document.getElementById('def-y').value = config.elements.definition.y_start;
            document.getElementById('def-size').value = config.elements.definition.font_size;
            document.getElementById('img-y').value = config.elements.image.y_start;
            document.getElementById('img-h').value = config.elements.image.height;
            document.getElementById('brand-y').value = config.elements.branding.y_start;
            document.getElementById('brand-size').value = config.elements.branding.font_size;
            document.getElementById('channel-name').value = config.branding.channel_name;
            
            ['word-y', 'word-size', 'def-y', 'def-size', 'img-y', 'img-h', 'brand-y', 'brand-size'].forEach(updateSlider);
            updatePreview();
            showToast('Configuration loaded');
        }

        function updateSlider(id) {
            const input = document.getElementById(id);
            const display = document.getElementById(`${id}-val`);
            display.textContent = input.value + 'px';
            updatePreview();
        }

        function updatePreview() {
            const scale = 1/3;
            const word = document.getElementById('preview-word').value;
            const def = document.getElementById('preview-def').value;
            const channel = document.getElementById('channel-name').value;
            
            const wordY = parseInt(document.getElementById('word-y').value) * scale;
            const wordSize = parseInt(document.getElementById('word-size').value) * scale;
            const defY = parseInt(document.getElementById('def-y').value) * scale;
            const defSize = parseInt(document.getElementById('def-size').value) * scale;
            const imgY = parseInt(document.getElementById('img-y').value) * scale;
            const imgH = parseInt(document.getElementById('img-h').value) * scale;
            const brandY = parseInt(document.getElementById('brand-y').value) * scale;
            const brandSize = parseInt(document.getElementById('brand-size').value) * scale;
            
            const bgColor = document.getElementById('bg-color').value;
            const wordColor = document.getElementById('word-color').value;
            const defColor = document.getElementById('def-color').value;
            const brandColor = document.getElementById('brand-color').value;
            
            let html = `<div style="width:360px;height:640px;background:${bgColor};position:relative;">`;
            
            if (showGuides) {
                html += `<div class="guide-vertical" style="left:90px;"></div>`;
                html += `<div class="guide-vertical" style="left:270px;"></div>`;
                html += `<div class="guide-line" style="top:${wordY}px;"></div>`;
                html += `<div class="guide-label" style="top:${wordY}px;left:5px;">${parseInt(document.getElementById('word-y').value)}px</div>`;
                html += `<div class="guide-line" style="top:${defY}px;"></div>`;
                html += `<div class="guide-line" style="top:${imgY}px;"></div>`;
                html += `<div class="guide-line" style="top:${brandY}px;"></div>`;
            }
            
            html += `<div style="position:absolute;top:${wordY}px;width:100%;text-align:center;font-size:${wordSize}px;font-weight:bold;color:${wordColor};padding:0 20px;">${word}</div>`;
            html += `<div style="position:absolute;top:${defY}px;width:100%;text-align:center;font-size:${defSize}px;color:${defColor};padding:0 30px;">${def}</div>`;
            html += `<div style="position:absolute;top:${imgY+imgH/3}px;left:50%;transform:translateX(-50%);width:${imgH*0.7}px;height:${imgH*0.7}px;background:#f0e6dc;border:2px solid #c8b8a0;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:${imgH/4}px;color:#968876;font-weight:bold;">[IMG]</div>`;
            html += `<div style="position:absolute;top:${brandY}px;width:100%;text-align:center;font-size:${brandSize}px;color:${brandColor};">${channel}</div>`;
            html += '</div>';
            
            document.getElementById('preview-box').innerHTML = html;
        }

        function toggleGuides() {
            showGuides = !showGuides;
            const btn = document.getElementById('guides-btn');
            btn.classList.toggle('bg-purple-100');
            btn.classList.toggle('text-purple-700');
            btn.classList.toggle('bg-gray-100');
            btn.classList.toggle('text-gray-600');
            updatePreview();
        }

        function applyTheme(theme) {
            const themes = {
                default: {bg:'#ffffff',word:'#232323',def:'#3c3c3c',brand:'#646464'},
                dark: {bg:'#1e1e1e',word:'#ffffff',def:'#dcdcdc',brand:'#b4b4b4'},
                blue: {bg:'#f0f8ff',word:'#003366',def:'#336699',brand:'#6699cc'}
            };
            const t = themes[theme];
            document.getElementById('bg-color').value = t.bg;
            document.getElementById('word-color').value = t.word;
            document.getElementById('def-color').value = t.def;
            document.getElementById('brand-color').value = t.brand;
            updatePreview();
        }

        async function loadFonts() {
            const res = await fetch('/api/fonts/google');
            const fonts = await res.json();
            const html = fonts.map(f => `
                <div class="font-item" onclick="selectFont('${f.name}')" style="font-family:'${f.name}',sans-serif;">
                    <div class="font-semibold text-gray-700">${f.name}</div>
                    <div style="font-size:24px;margin:8px 0;">The quick brown fox</div>
                </div>
            `).join('');
            document.getElementById('fonts-list').innerHTML = html;
            
            const link = document.createElement('link');
            link.href = `https://fonts.googleapis.com/css2?${fonts.map(f => `family=${f.name.replace(' ','+')}:wght@${f.weights.join(';')}`).join('&')}&display=swap`;
            link.rel = 'stylesheet';
            document.head.appendChild(link);
        }

        function selectFont(font) {
            if(config) config.typography.font_family = font;
            document.querySelectorAll('.font-item').forEach(i => i.classList.remove('selected'));
            event.target.closest('.font-item').classList.add('selected');
            showToast(`Font: ${font}`);
        }

        async function uploadFont() {
            const file = document.getElementById('font-upload').files[0];
            if(!file) return;
            
            const formData = new FormData();
            formData.append('font_file', file);
            
            const res = await fetch('/api/fonts/upload', {method:'POST', body:formData});
            const result = await res.json();
            
            if(result.success) showToast('Font uploaded!');
            else alert('Upload failed: ' + result.error);
        }

        async function saveConfig() {
            const newConfig = {
                ...config,
                elements: {
                    word_title: {...config.elements.word_title, y_start:parseInt(document.getElementById('word-y').value), font_size:parseInt(document.getElementById('word-size').value)},
                    definition: {...config.elements.definition, y_start:parseInt(document.getElementById('def-y').value), font_size:parseInt(document.getElementById('def-size').value)},
                    image: {...config.elements.image, y_start:parseInt(document.getElementById('img-y').value), height:parseInt(document.getElementById('img-h').value)},
                    branding: {...config.elements.branding, y_start:parseInt(document.getElementById('brand-y').value), font_size:parseInt(document.getElementById('brand-size').value)}
                },
                branding: {...config.branding, channel_name:document.getElementById('channel-name').value}
            };
            
            const res = await fetch('/api/layout/config', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify(newConfig)
            });
            
            const result = await res.json();
            if(result.success) {
                config = newConfig;
                showToast('Configuration saved!');
            } else alert('Save failed: ' + result.error);
        }

        async function downloadPreview() {
            const res = await fetch('/api/preview/download', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({
                    word:document.getElementById('preview-word').value,
                    definition:document.getElementById('preview-def').value,
                    show_guides:showGuides
                })
            });
            
            if(res.ok) {
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'preview.png';
                a.click();
                URL.revokeObjectURL(url);
                showToast('Preview downloaded!');
            }
        }

        function downloadConfig() {
            const blob = new Blob([JSON.stringify(config, null, 2)], {type:'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'layout_config.json';
            a.click();
            URL.revokeObjectURL(url);
            showToast('Config exported!');
        }

        function showToast(msg) {
            document.getElementById('toast-msg').textContent = msg;
            document.getElementById('toast').style.display = 'block';
            setTimeout(() => document.getElementById('toast').style.display = 'none', 3000);
        }
    </script>
</body>
</html>
'''
