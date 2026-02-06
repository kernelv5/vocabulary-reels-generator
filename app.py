#!/usr/bin/env python3
"""
Vocabulary Reels Generator - API Server
========================================

Web UI and REST API for generating YouTube Shorts vocabulary videos.

Run with Docker:
    docker-compose up -d

Or locally:
    python app.py

API Endpoints:
    GET  /                        - Web UI
    GET  /api/health              - Health check
    GET  /api/status              - Check all services status
    GET  /api/words               - List all vocabulary words
    POST /api/words               - Add a new word
    DELETE /api/words/<index>     - Delete a word
    POST /api/generate            - Generate video for a word
    POST /api/generate/<index>    - Generate video by word index
    POST /api/generate/image      - Generate image only (preview)
    POST /api/generate/audio      - Generate audio only (preview)
    POST /api/generate/batch      - Generate videos for all pending words
    POST /api/upload/csv          - Upload CSV file with vocabulary
    POST /api/upload/image        - Upload custom image
    GET  /api/download/<filename> - Download generated file
    GET  /api/files               - List all output files
    GET  /output/<filename>       - Serve output files
"""

import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory, render_template_string
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from src.csv_reader import (
    load_vocabulary, save_vocabulary, add_word, delete_word,
    get_all_words, get_word_by_index, clear_all_words
)
from src.generator_v2 import VideoGeneratorV2

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for n8n integration

# File upload settings
ALLOWED_EXTENSIONS = {'csv', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Generator instance - Using V2 that reads from layout_config.json
generator = VideoGeneratorV2()


def allowed_file(filename, extensions=None):
    """Check if file extension is allowed."""
    extensions = extensions or ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions


# ============================================
# WEB UI - Complete HTML/CSS/JS
# ============================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vocabulary Reels Generator</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06); }
        .status-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
        .status-green { background-color: #10b981; box-shadow: 0 0 8px #10b981; }
        .status-red { background-color: #ef4444; box-shadow: 0 0 8px #ef4444; }
        .status-yellow { background-color: #f59e0b; animation: pulse 2s infinite; }
        .fade-in { animation: fadeIn 0.3s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .progress-bar { transition: width 0.5s ease; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .btn-primary:hover { background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%); transform: translateY(-1px); }
        .word-card { transition: all 0.2s ease; }
        .word-card:hover { transform: translateX(4px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .loading-spinner { border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 24px; height: 24px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Header -->
    <header class="gradient-bg text-white py-8 shadow-lg">
        <div class="container mx-auto px-6">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold flex items-center gap-3">
                        <i class="fas fa-video"></i>
                        Vocabulary Reels Generator
                    </h1>
                    <p class="text-purple-200 mt-2">Create YouTube Shorts-style vocabulary videos with AI</p>
                </div>
                <div class="flex items-center gap-4">
                    <!-- Tools Dropdown -->
                    <div class="relative" id="tools-dropdown">
                        <button onclick="toggleToolsMenu()" class="flex items-center gap-2 bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition">
                            <i class="fas fa-tools"></i>
                            <span>Tools</span>
                            <i class="fas fa-chevron-down text-sm"></i>
                        </button>
                        <div id="tools-menu" class="hidden absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-xl z-50 overflow-hidden">
                            <a href="/layout-editor" class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-purple-50 transition">
                                <i class="fas fa-sliders-h text-purple-600"></i>
                                <span>Layout Editor</span>
                            </a>
                            <a href="/image-generator" class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-purple-50 transition">
                                <i class="fas fa-image text-green-600"></i>
                                <span>Image Generator</span>
                            </a>
                            <a href="/csv-generator" class="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-purple-50 transition">
                                <i class="fas fa-file-csv text-orange-600"></i>
                                <span>CSV Generator</span>
                            </a>
                        </div>
                    </div>
                    <div class="text-right text-sm text-purple-200">
                        <div id="version-info" class="font-mono text-xs cursor-pointer hover:text-white" onclick="toggleVersionDetails()">
                            <span id="version-branch">Loading...</span> • <span id="version-commit">...</span>
                        </div>
                        <div id="container-status" class="font-mono">Running</div>
                    </div>
                    <!-- Version Details Popup -->
                    <div id="version-details" class="hidden absolute right-6 top-20 bg-white text-gray-800 rounded-lg shadow-xl z-50 p-4 w-72">
                        <h3 class="font-bold text-purple-600 mb-2 flex items-center gap-2">
                            <i class="fas fa-code-branch"></i> Version Info
                        </h3>
                        <div class="space-y-2 text-sm">
                            <div class="flex justify-between">
                                <span class="text-gray-500">Version:</span>
                                <span id="detail-version" class="font-mono">-</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-gray-500">Branch:</span>
                                <span id="detail-branch" class="font-mono">-</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-gray-500">Commit:</span>
                                <span id="detail-commit" class="font-mono">-</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-gray-500">Updated:</span>
                                <span id="detail-date" class="font-mono text-xs">-</span>
                            </div>
                            <div class="pt-2 border-t border-gray-200">
                                <span class="text-gray-500 text-xs" id="detail-description">-</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <main class="container mx-auto px-6 py-8">
        <!-- Status Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="card p-5">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm font-medium">ComfyUI (Image AI)</p>
                        <p class="text-xl font-bold mt-1" id="comfyui-status">Checking...</p>
                        <p class="text-xs text-gray-400 mt-1" id="comfyui-url"></p>
                    </div>
                    <div class="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
                        <span class="status-dot status-yellow" id="comfyui-dot"></span>
                    </div>
                </div>
            </div>
            <div class="card p-5">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm font-medium">TTS Server (Voice AI)</p>
                        <p class="text-xl font-bold mt-1" id="tts-status">Checking...</p>
                        <p class="text-xs text-gray-400 mt-1" id="tts-url"></p>
                    </div>
                    <div class="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                        <span class="status-dot status-yellow" id="tts-dot"></span>
                    </div>
                </div>
            </div>
            <div class="card p-5">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm font-medium">FFmpeg (Video)</p>
                        <p class="text-xl font-bold mt-1" id="ffmpeg-status">Checking...</p>
                        <p class="text-xs text-gray-400 mt-1">Video encoding</p>
                    </div>
                    <div class="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                        <span class="status-dot status-yellow" id="ffmpeg-dot"></span>
                    </div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Left Column -->
            <div class="space-y-6">
                <!-- Single Word Generator -->
                <div class="card p-6">
                    <h2 class="text-xl font-bold mb-6 flex items-center gap-2">
                        <i class="fas fa-magic text-purple-600"></i>
                        Generate Video
                    </h2>
                    
                    <form id="generate-form" class="space-y-5">
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Word *</label>
                            <input type="text" id="word" name="word" required
                                   class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition"
                                   placeholder="e.g., Serendipity">
                        </div>
                        
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Definition *</label>
                            <textarea id="definition" name="definition" required rows="2"
                                      class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition"
                                      placeholder="e.g., Finding something good by happy chance"></textarea>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Example Sentence (optional)</label>
                            <input type="text" id="example" name="example"
                                   class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition"
                                   placeholder="e.g., Meeting her was pure serendipity.">
                        </div>
                        
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">
                                <i class="fas fa-wand-magic-sparkles mr-1"></i> Image Prompt Guideline (optional)
                            </label>
                            <textarea id="prompt-image-guideline" name="prompt_image_guideline" rows="2"
                                      class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition"
                                      placeholder="e.g., A happy person finding a treasure chest by accident, warm colors, minimalist style"></textarea>
                            <p class="text-xs text-gray-500 mt-1">Custom description for AI image generation (uses definition if empty)</p>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">
                                <i class="fas fa-image mr-1"></i> Custom Image (optional)
                            </label>
                            <input type="file" id="custom-image" name="custom_image" accept="image/*"
                                   class="w-full px-4 py-3 border-2 border-dashed border-gray-300 rounded-xl hover:border-purple-400 transition cursor-pointer">
                            <p class="text-xs text-gray-500 mt-2">Upload your own image instead of AI-generated (PNG, JPG)</p>
                        </div>
                        
                        <!-- Vocabulary Type & Revision -->
                        <div class="grid grid-cols-3 gap-3">
                            <div>
                                <label class="block text-sm font-semibold text-gray-700 mb-2">
                                    <i class="fas fa-tag mr-1"></i> Type
                                </label>
                                <select id="vocabulary-type" name="vocabulary_type"
                                        class="w-full px-3 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition">
                                    <option value="GeneralEnglish" selected>General English</option>
                                    <option value="BusinessEnglish">Business English</option>
                                    <option value="AcademicEnglish">Academic English</option>
                                    <option value="IELTS">IELTS</option>
                                    <option value="TOEFL">TOEFL</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm font-semibold text-gray-700 mb-2">Revision</label>
                                <input type="number" id="revision" name="revision" value="1" min="1" max="99"
                                       class="w-full px-3 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition">
                            </div>
                            <div>
                                <label class="block text-sm font-semibold text-gray-700 mb-2">Target</label>
                                <input type="number" id="target-revision" name="target_revision" value="5" min="1" max="99"
                                       class="w-full px-3 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition">
                            </div>
                        </div>
                        
                        <div class="flex gap-3 pt-2">
                            <button type="submit" id="generate-btn"
                                    class="flex-1 btn-primary text-white py-3 px-6 rounded-xl font-semibold transition flex items-center justify-center gap-2 shadow-lg">
                                <i class="fas fa-film"></i>
                                Generate Video
                            </button>
                            <button type="button" onclick="previewImage()" title="Preview Image Only"
                                    class="bg-gray-100 text-gray-700 py-3 px-4 rounded-xl hover:bg-gray-200 transition">
                                <i class="fas fa-image"></i>
                            </button>
                            <button type="button" onclick="previewAudio()" title="Preview Audio Only"
                                    class="bg-gray-100 text-gray-700 py-3 px-4 rounded-xl hover:bg-gray-200 transition">
                                <i class="fas fa-volume-up"></i>
                            </button>
                        </div>
                    </form>
                    
                    <!-- Progress -->
                    <div id="progress-container" class="mt-6 hidden">
                        <div class="flex justify-between text-sm mb-2">
                            <span id="progress-step" class="font-medium text-gray-700">Initializing...</span>
                            <span id="progress-percent" class="font-bold text-purple-600">0%</span>
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                            <div id="progress-bar" class="bg-gradient-to-r from-purple-500 to-indigo-600 h-3 rounded-full progress-bar" style="width: 0%"></div>
                        </div>
                    </div>
                </div>

                <!-- CSV Upload -->
                <div class="card p-6">
                    <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                        <i class="fas fa-file-csv text-green-600"></i>
                        Bulk Import (CSV)
                    </h2>
                    
                    <form id="csv-form" class="space-y-4">
                        <div class="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-green-400 transition">
                            <input type="file" id="csv-file" name="csv_file" accept=".csv" required class="hidden">
                            <label for="csv-file" class="cursor-pointer">
                                <i class="fas fa-cloud-upload-alt text-4xl text-gray-400 mb-2"></i>
                                <p class="text-gray-600 font-medium">Click to upload CSV file</p>
                                <p class="text-xs text-gray-400 mt-1">Columns: word, definition, example (optional)</p>
                            </label>
                        </div>
                        <button type="submit"
                                class="w-full bg-green-600 text-white py-3 px-4 rounded-xl font-semibold hover:bg-green-700 transition shadow">
                            <i class="fas fa-upload mr-2"></i>
                            Upload & Import
                        </button>
                    </form>
                </div>
            </div>

            <!-- Right Column -->
            <div class="space-y-6">
                <!-- Generated Video Preview -->
                <div id="result-container" class="card p-6 hidden fade-in">
                    <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                        <i class="fas fa-check-circle text-green-600"></i>
                        Video Ready!
                    </h2>
                    <div class="flex justify-center">
                        <video id="result-video" controls class="rounded-xl mb-4 shadow-lg" style="width: 270px; height: 480px; object-fit: contain; background: #000;"></video>
                    </div>
                    <a id="download-link" href="#" download
                       class="block w-full bg-blue-600 text-white py-3 px-4 rounded-xl font-semibold hover:bg-blue-700 transition text-center shadow">
                        <i class="fas fa-download mr-2"></i>
                        Download Video
                    </a>
                </div>

                <!-- Word List -->
                <div class="card p-6">
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-xl font-bold flex items-center gap-2">
                            <i class="fas fa-list text-blue-600"></i>
                            Vocabulary List
                            <span id="word-count" class="text-sm font-normal text-gray-500">(0 words)</span>
                        </h2>
                        <div class="flex gap-2">
                            <button onclick="clearVocabularyList()" class="text-red-500 hover:text-red-700" title="Clear All Words">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                            <button onclick="generateBatch()"
                                    class="bg-indigo-600 text-white py-2 px-4 rounded-lg hover:bg-indigo-700 transition text-sm font-medium shadow">
                                <i class="fas fa-play mr-1"></i>
                                Generate All
                            </button>
                        </div>
                    </div>
                    
                    <!-- Batch Progress -->
                    <div id="batch-progress-container" class="hidden mb-4 p-4 bg-indigo-50 rounded-xl">
                        <div class="flex justify-between items-center mb-2">
                            <span id="batch-progress-text" class="text-sm font-medium text-indigo-700">Generating...</span>
                            <span id="batch-progress-count" class="text-sm font-bold text-indigo-600">0/0</span>
                        </div>
                        <div class="w-full bg-indigo-200 rounded-full h-3 overflow-hidden">
                            <div id="batch-progress-bar" class="bg-indigo-600 h-3 rounded-full transition-all duration-300" style="width: 0%"></div>
                        </div>
                    </div>
                    
                    <div id="word-list" class="space-y-2 max-h-80 overflow-y-auto pr-2">
                        <div class="flex items-center justify-center py-8">
                            <div class="loading-spinner"></div>
                        </div>
                    </div>
                </div>

                <!-- Output Files -->
                <div class="card p-6">
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-xl font-bold flex items-center gap-2">
                            <i class="fas fa-folder-open text-yellow-600"></i>
                            Output Files
                        </h2>
                        <div class="flex gap-2">
                            <button onclick="clearOutputFiles()" class="text-red-500 hover:text-red-700" title="Clear All Files">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                            <button onclick="loadOutputFiles()" class="text-gray-500 hover:text-gray-700" title="Refresh">
                                <i class="fas fa-sync-alt"></i>
                            </button>
                        </div>
                    </div>
                    <div id="output-files" class="space-y-2 max-h-64 overflow-y-auto pr-2">
                        <div class="flex items-center justify-center py-8">
                            <div class="loading-spinner"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- API Documentation -->
        <div class="card p-6 mt-8">
            <h2 class="text-xl font-bold mb-6 flex items-center gap-2">
                <i class="fas fa-code text-indigo-600"></i>
                API Endpoints (for n8n / Automation)
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                <div class="bg-gray-50 p-4 rounded-xl">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="bg-green-100 text-green-700 px-2 py-1 rounded text-xs font-bold">GET</span>
                        <code class="font-mono">/api/status</code>
                    </div>
                    <p class="text-gray-500">Check all services status</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="bg-green-100 text-green-700 px-2 py-1 rounded text-xs font-bold">GET</span>
                        <code class="font-mono">/api/words</code>
                    </div>
                    <p class="text-gray-500">List all vocabulary words</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-bold">POST</span>
                        <code class="font-mono">/api/words</code>
                    </div>
                    <p class="text-gray-500">Add word: {word, definition, example}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-bold">POST</span>
                        <code class="font-mono">/api/generate</code>
                    </div>
                    <p class="text-gray-500">Generate video: {word, definition}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-bold">POST</span>
                        <code class="font-mono">/api/generate/batch</code>
                    </div>
                    <p class="text-gray-500">Generate all pending videos</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-xl">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="bg-green-100 text-green-700 px-2 py-1 rounded text-xs font-bold">GET</span>
                        <code class="font-mono">/api/download/{file}</code>
                    </div>
                    <p class="text-gray-500">Download generated file</p>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="text-center py-6 text-gray-500 text-sm">
        <p>Vocabulary Reels Generator | Running in Docker</p>
    </footer>

    <script>
        // Toggle tools dropdown menu
        function toggleToolsMenu() {
            const menu = document.getElementById('tools-menu');
            menu.classList.toggle('hidden');
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            const dropdown = document.getElementById('tools-dropdown');
            const menu = document.getElementById('tools-menu');
            if (dropdown && !dropdown.contains(e.target)) {
                menu.classList.add('hidden');
            }
            // Close version details when clicking outside
            const versionDetails = document.getElementById('version-details');
            const versionInfo = document.getElementById('version-info');
            if (versionDetails && versionInfo && !versionDetails.contains(e.target) && !versionInfo.contains(e.target)) {
                versionDetails.classList.add('hidden');
            }
        });

        // Toggle version details popup
        function toggleVersionDetails() {
            const details = document.getElementById('version-details');
            details.classList.toggle('hidden');
        }

        // Load version info
        async function loadVersionInfo() {
            try {
                const res = await fetch('/api/version');
                const data = await res.json();
                
                document.getElementById('version-branch').textContent = data.branch || 'unknown';
                document.getElementById('version-commit').textContent = data.commit || '---';
                
                document.getElementById('detail-version').textContent = data.version || '-';
                document.getElementById('detail-branch').textContent = data.branch || '-';
                document.getElementById('detail-commit').textContent = data.commit || '-';
                document.getElementById('detail-date').textContent = data.last_updated || data.commit_date || '-';
                document.getElementById('detail-description').textContent = data.description || '-';
            } catch (e) {
                console.error('Version info load failed:', e);
                document.getElementById('version-branch').textContent = 'dev';
                document.getElementById('version-commit').textContent = 'local';
            }
        }

        // Check services status
        async function checkStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                // ComfyUI
                document.getElementById('comfyui-status').textContent = data.comfyui.running ? 'Connected' : 'Offline';
                document.getElementById('comfyui-dot').className = 'status-dot ' + (data.comfyui.running ? 'status-green' : 'status-red');
                document.getElementById('comfyui-url').textContent = data.comfyui.url;
                
                // TTS
                document.getElementById('tts-status').textContent = data.tts.running ? 'Connected' : 'Offline';
                document.getElementById('tts-dot').className = 'status-dot ' + (data.tts.running ? 'status-green' : 'status-red');
                document.getElementById('tts-url').textContent = data.tts.url;
                
                // FFmpeg
                document.getElementById('ffmpeg-status').textContent = data.ffmpeg.installed ? 'Installed' : 'Missing';
                document.getElementById('ffmpeg-dot').className = 'status-dot ' + (data.ffmpeg.installed ? 'status-green' : 'status-red');
            } catch (e) {
                console.error('Status check failed:', e);
            }
        }

        // Load word list
        async function loadWords() {
            try {
                const res = await fetch('/api/words');
                const words = await res.json();
                
                document.getElementById('word-count').textContent = `(${words.length} words)`;
                
                const container = document.getElementById('word-list');
                if (words.length === 0) {
                    container.innerHTML = '<p class="text-gray-400 text-center py-8">No words yet. Add some above!</p>';
                    return;
                }
                
                container.innerHTML = words.map(w => {
                    const statusColor = w.status === 'completed' ? 'border-l-4 border-green-500 bg-green-50' : 
                                       w.status.startsWith('failed') ? 'border-l-4 border-red-500 bg-red-50' : 
                                       'border-l-4 border-gray-300';
                    const statusIcon = w.status === 'completed' ? '<i class="fas fa-check-circle text-green-500"></i>' :
                                      w.status.startsWith('failed') ? '<i class="fas fa-exclamation-circle text-red-500"></i>' :
                                      '<i class="fas fa-clock text-gray-400"></i>';
                    return `
                        <div class="word-card flex items-center justify-between p-3 rounded-lg ${statusColor}">
                            <div class="flex items-center gap-3">
                                ${statusIcon}
                                <div>
                                    <span class="font-semibold text-gray-800">${w.word}</span>
                                    <p class="text-gray-500 text-xs truncate max-w-xs">${w.definition}</p>
                                </div>
                            </div>
                            <div class="flex gap-2">
                                ${w.status === 'completed' && w.video_path ? `
                                    <a href="/output/${w.video_path.split('/').pop()}" target="_blank" 
                                       class="text-blue-600 hover:text-blue-800 p-2" title="Play Video">
                                        <i class="fas fa-play"></i>
                                    </a>
                                    <a href="/api/download/${w.video_path.split('/').pop()}" 
                                       class="text-green-600 hover:text-green-800 p-2" title="Download Video">
                                        <i class="fas fa-download"></i>
                                    </a>
                                ` : ''}
                                <button onclick="generateSingle(${w.index})" class="text-purple-600 hover:text-purple-800 p-2" title="Regenerate">
                                    <i class="fas fa-redo"></i>
                                </button>
                                <button onclick="deleteWord(${w.index})" class="text-red-500 hover:text-red-700 p-2" title="Delete">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('Failed to load words:', e);
                document.getElementById('word-list').innerHTML = '<p class="text-red-500 text-center py-4">Failed to load words</p>';
            }
        }

        // Load output files
        async function loadOutputFiles() {
            try {
                const res = await fetch('/api/files');
                const files = await res.json();
                
                const container = document.getElementById('output-files');
                if (files.length === 0) {
                    container.innerHTML = '<p class="text-gray-400 text-center py-8">No files generated yet</p>';
                    return;
                }
                
                container.innerHTML = files.slice(0, 20).map(f => {
                    const icon = f.type === '.mp4' ? 'fa-video text-purple-500' : 
                                f.type === '.mp3' ? 'fa-music text-blue-500' : 
                                'fa-image text-green-500';
                    const size = (f.size / 1024 / 1024).toFixed(2);
                    return `
                        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                            <div class="flex items-center gap-3">
                                <i class="fas ${icon}"></i>
                                <span class="text-sm font-medium text-gray-700 truncate max-w-xs">${f.name}</span>
                                <span class="text-xs text-gray-400">${size}MB</span>
                            </div>
                            <a href="/api/download/${f.name}" class="text-blue-600 hover:text-blue-800 p-2">
                                <i class="fas fa-download"></i>
                            </a>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('Failed to load files:', e);
            }
        }

        // Generate video form submit
        document.getElementById('generate-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btn = document.getElementById('generate-btn');
            btn.disabled = true;
            btn.innerHTML = '<div class="loading-spinner mx-auto"></div>';
            
            const formData = new FormData();
            formData.append('word', document.getElementById('word').value);
            formData.append('definition', document.getElementById('definition').value);
            formData.append('example', document.getElementById('example').value || '');
            formData.append('prompt_image_guideline', document.getElementById('prompt-image-guideline').value || '');
            formData.append('vocabulary_type', document.getElementById('vocabulary-type').value || 'GeneralEnglish');
            formData.append('revision', document.getElementById('revision').value || '1');
            formData.append('target_revision', document.getElementById('target-revision').value || '5');
            
            const imageFile = document.getElementById('custom-image').files[0];
            if (imageFile) {
                formData.append('custom_image', imageFile);
            }
            
            // Show progress
            document.getElementById('progress-container').classList.remove('hidden');
            document.getElementById('result-container').classList.add('hidden');
            updateProgress('Starting...', 5);
            
            try {
                // Simulate progress updates
                const progressInterval = setInterval(() => {
                    const currentWidth = parseInt(document.getElementById('progress-bar').style.width) || 0;
                    if (currentWidth < 90) {
                        updateProgress('Processing...', currentWidth + Math.random() * 10);
                    }
                }, 2000);
                
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    body: formData
                });
                
                clearInterval(progressInterval);
                const data = await res.json();
                
                if (data.success) {
                    updateProgress('Completed!', 100);
                    
                    // Show result
                    setTimeout(() => {
                        document.getElementById('result-container').classList.remove('hidden');
                        document.getElementById('result-video').src = `/output/${data.video_filename}`;
                        document.getElementById('download-link').href = `/api/download/${data.video_filename}`;
                        
                        // Clear form
                        document.getElementById('generate-form').reset();
                        
                        // Refresh lists
                        loadWords();
                        loadOutputFiles();
                    }, 500);
                } else {
                    updateProgress('Failed: ' + data.error, 0);
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                updateProgress('Request failed', 0);
                alert('Request failed: ' + e.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-film"></i> Generate Video';
            }
        });

        function updateProgress(step, percent) {
            document.getElementById('progress-step').textContent = step;
            document.getElementById('progress-percent').textContent = Math.round(percent) + '%';
            document.getElementById('progress-bar').style.width = percent + '%';
        }

        // Preview image
        async function previewImage() {
            const word = document.getElementById('word').value;
            const definition = document.getElementById('definition').value;
            
            if (!word || !definition) {
                alert('Please enter word and definition');
                return;
            }
            
            try {
                const res = await fetch('/api/generate/image', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({word, definition})
                });
                const data = await res.json();
                
                if (data.success) {
                    window.open(`/output/${data.image_filename}`, '_blank');
                    loadOutputFiles();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                alert('Request failed: ' + e.message);
            }
        }

        // Preview audio
        async function previewAudio() {
            const word = document.getElementById('word').value;
            const definition = document.getElementById('definition').value;
            const example = document.getElementById('example').value;
            
            if (!word || !definition) {
                alert('Please enter word and definition');
                return;
            }
            
            try {
                const res = await fetch('/api/generate/audio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({word, definition, example})
                });
                const data = await res.json();
                
                if (data.success) {
                    const audio = new Audio(`/output/${data.audio_filename}`);
                    audio.play();
                    loadOutputFiles();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                alert('Request failed: ' + e.message);
            }
        }

        // Delete word
        async function deleteWord(index) {
            if (!confirm('Delete this word?')) return;
            
            try {
                await fetch(`/api/words/${index}`, {method: 'DELETE'});
                loadWords();
            } catch (e) {
                alert('Delete failed');
            }
        }

        // Generate single from list
        async function generateSingle(index) {
            if (!confirm('Generate/regenerate video for this word?')) return;
            
            try {
                const res = await fetch(`/api/generate/${index}`, {method: 'POST'});
                const data = await res.json();
                
                if (data.success) {
                    alert('Video generated successfully!');
                    loadWords();
                    loadOutputFiles();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                alert('Generation failed: ' + e.message);
            }
        }

        // Generate batch with progress
        async function generateBatch() {
            if (!confirm('Generate videos for all pending words? This may take a while.')) return;
            
            // Show progress container
            const progressContainer = document.getElementById('batch-progress-container');
            const progressBar = document.getElementById('batch-progress-bar');
            const progressText = document.getElementById('batch-progress-text');
            const progressCount = document.getElementById('batch-progress-count');
            
            progressContainer.classList.remove('hidden');
            progressBar.style.width = '0%';
            progressText.textContent = 'Starting batch generation...';
            progressCount.textContent = '0/0';
            
            try {
                // First get the count of pending words
                const wordsRes = await fetch('/api/words');
                const allWords = await wordsRes.json();
                const pendingWords = allWords.filter(w => w.status === 'pending');
                const total = pendingWords.length;
                
                if (total === 0) {
                    progressContainer.classList.add('hidden');
                    alert('No pending words to generate.');
                    return;
                }
                
                progressCount.textContent = `0/${total}`;
                progressText.textContent = 'Generating videos...';
                
                // Generate one by one with progress
                let successCount = 0;
                let failCount = 0;
                const generatedFiles = [];
                
                for (let i = 0; i < pendingWords.length; i++) {
                    const word = pendingWords[i];
                    progressText.textContent = `Generating: ${word.word}`;
                    progressCount.textContent = `${i}/${total}`;
                    progressBar.style.width = `${(i / total) * 100}%`;
                    
                    try {
                        const res = await fetch(`/api/generate/${word.index}`, {method: 'POST'});
                        const result = await res.json();
                        
                        if (result.success) {
                            successCount++;
                            if (result.video_path) {
                                const filename = result.video_path.split('/').pop().split('\\\\').pop();
                                generatedFiles.push(filename);
                            }
                        } else {
                            failCount++;
                        }
                    } catch (err) {
                        failCount++;
                    }
                    
                    progressCount.textContent = `${i + 1}/${total}`;
                    progressBar.style.width = `${((i + 1) / total) * 100}%`;
                }
                
                // Complete
                progressText.textContent = 'Batch complete!';
                progressBar.style.width = '100%';
                
                setTimeout(() => {
                    progressContainer.classList.add('hidden');
                    
                    if (generatedFiles.length > 0) {
                        showBatchDownloadModal(generatedFiles);
                    } else {
                        alert(`Batch complete!\n✓ Success: ${successCount}\n✗ Failed: ${failCount}`);
                    }
                    
                    loadWords();
                    loadOutputFiles();
                }, 1000);
                
            } catch (e) {
                progressContainer.classList.add('hidden');
                alert('Batch generation failed: ' + e.message);
            }
        }
        
        // Clear vocabulary list
        async function clearVocabularyList() {
            if (!confirm('Delete ALL vocabulary words? This cannot be undone!')) return;
            
            try {
                const res = await fetch('/api/words/clear', {method: 'DELETE'});
                const data = await res.json();
                if (data.success) {
                    alert(`Cleared ${data.deleted_count} word(s)`);
                    loadWords();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                alert('Failed to clear words: ' + e.message);
            }
        }
        
        // Show batch download modal
        function showBatchDownloadModal(files) {
            const modal = document.createElement('div');
            modal.id = 'batch-modal';
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
            modal.innerHTML = `
                <div class="bg-white rounded-2xl p-6 max-w-lg w-full mx-4 max-h-96 overflow-auto">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xl font-bold text-green-600"><i class="fas fa-check-circle mr-2"></i>Batch Complete!</h3>
                        <button onclick="document.getElementById('batch-modal').remove()" class="text-gray-500 hover:text-gray-700">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>
                    <p class="text-gray-600 mb-4">${files.length} video(s) generated successfully:</p>
                    <div class="space-y-2">
                        ${files.map(f => `
                            <a href="/api/download/${f}" download 
                               class="flex items-center gap-2 p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition">
                                <i class="fas fa-download text-blue-600"></i>
                                <span class="text-sm truncate">${f}</span>
                            </a>
                        `).join('')}
                    </div>
                    <button onclick="downloadAllBatch([${files.map(f => "'" + f + "'").join(',')}])" 
                            class="mt-4 w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition">
                        <i class="fas fa-download mr-2"></i>Download All
                    </button>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        // Download all batch files
        async function downloadAllBatch(files) {
            for (const file of files) {
                const a = document.createElement('a');
                a.href = `/api/download/${file}`;
                a.download = file;
                a.click();
                await new Promise(r => setTimeout(r, 500)); // Small delay between downloads
            }
        }
        
        // Clear output files
        async function clearOutputFiles() {
            if (!confirm('Delete ALL output files? This cannot be undone!')) return;
            
            try {
                const res = await fetch('/api/files/clear', {method: 'DELETE'});
                const data = await res.json();
                if (data.success) {
                    alert(`Deleted ${data.deleted_count} file(s)`);
                    loadOutputFiles();
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                alert('Failed to clear files: ' + e.message);
            }
        }

        // Upload CSV
        document.getElementById('csv-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const fileInput = document.getElementById('csv-file');
            if (!fileInput.files[0]) {
                alert('Please select a CSV file');
                return;
            }
            
            const formData = new FormData();
            formData.append('csv_file', fileInput.files[0]);
            
            try {
                const res = await fetch('/api/upload/csv', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                
                if (data.success) {
                    alert(`Successfully imported ${data.count} words!`);
                    loadWords();
                    fileInput.value = '';
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                alert('Upload failed: ' + e.message);
            }
        });

        // File input label update
        document.getElementById('csv-file').addEventListener('change', function(e) {
            const label = this.parentElement.querySelector('p');
            if (this.files[0]) {
                label.textContent = this.files[0].name;
            }
        });

        // Initial load
        checkStatus();
        loadWords();
        loadOutputFiles();
        loadVersionInfo();
        
        // Auto-refresh status every 30s
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>
'''


# ============================================
# ROUTES
# ============================================

# ============================================
# LAYOUT EDITOR HTML TEMPLATE
# ============================================

LAYOUT_EDITOR_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Layout Editor - Vocabulary Reels</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 24px; }
        .preview-box { width: 270px; height: 480px; background: white; margin: 0 auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3); border-radius: 16px; overflow: hidden; border: 6px solid #333; position: relative; }
        .toast { position: fixed; bottom: 30px; right: 30px; padding: 16px 24px; border-radius: 12px; z-index: 1000; display: none; color: white; }
        .toast.success { background: #10b981; }
        .toast.error { background: #ef4444; }
        .input-group { display: flex; gap: 8px; align-items: center; }
        .input-group input[type="number"] { width: 80px; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; text-align: center; }
        .input-group label { min-width: 30px; font-weight: 600; }
        .section-title { font-size: 14px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #e5e7eb; }
        .element-card { background: #f9fafb; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
        .element-card h4 { font-weight: 700; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
        .btn { padding: 10px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(102,126,234,0.4); }
        .btn-success { background: #10b981; color: white; }
        .btn-success:hover { background: #059669; }
        .btn-secondary { background: #6b7280; color: white; }
        .btn-secondary:hover { background: #4b5563; }
        .btn-outline { background: white; border: 2px solid #d1d5db; color: #374151; }
        .btn-outline:hover { border-color: #667eea; color: #667eea; }
        .guide-line { position: absolute; left: 0; right: 0; height: 1px; background: rgba(239, 68, 68, 0.5); pointer-events: none; }
        .guide-line::after { content: attr(data-label); position: absolute; right: 4px; top: -10px; font-size: 8px; color: #ef4444; background: white; padding: 0 2px; }
        .safe-area { position: absolute; border: 1px dashed rgba(102, 126, 234, 0.5); background: rgba(102, 126, 234, 0.05); pointer-events: none; }
        .element-preview { position: absolute; text-align: center; transition: all 0.15s ease; }
        .specs-panel { font-size: 11px; color: #6b7280; margin-top: 16px; padding: 12px; background: #f3f4f6; border-radius: 8px; }
        .specs-panel table { width: 100%; }
        .specs-panel td { padding: 2px 4px; }
        .specs-panel td:first-child { font-weight: 600; }
    </style>
</head>
<body class="bg-gray-50">
    <header class="gradient-bg text-white py-4">
        <div class="container mx-auto px-6">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                    <a href="/" class="hover:text-purple-200"><i class="fas fa-arrow-left text-xl"></i></a>
                    <h1 class="text-2xl font-bold"><i class="fas fa-sliders-h mr-2"></i>Layout Editor</h1>
                </div>
                <div class="flex gap-2">
                    <button onclick="reloadConfig()" class="btn btn-outline" style="background:rgba(255,255,255,0.1);border-color:rgba(255,255,255,0.3);color:white;">
                        <i class="fas fa-sync-alt"></i> Reload
                    </button>
                    <button onclick="downloadConfig()" class="btn btn-outline" style="background:rgba(255,255,255,0.1);border-color:rgba(255,255,255,0.3);color:white;">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <label class="btn btn-outline" style="background:rgba(255,255,255,0.1);border-color:rgba(255,255,255,0.3);color:white;cursor:pointer;">
                        <i class="fas fa-upload"></i> Import
                        <input type="file" accept=".json" onchange="importConfig(event)" style="display:none;">
                    </label>
                </div>
            </div>
        </div>
    </header>
    
    <main class="container mx-auto px-6 py-6">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Controls Panel -->
            <div class="lg:col-span-2 space-y-4">
                <!-- Word Title -->
                <div class="card">
                    <div class="section-title"><i class="fas fa-heading text-purple-500"></i> Word Title</div>
                    <div class="element-card">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="input-group">
                                <label>Y:</label>
                                <input type="number" id="word-y" min="0" max="800" value="175" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>H:</label>
                                <input type="number" id="word-h" min="20" max="200" value="55" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-4 mt-3">
                            <div class="input-group">
                                <label>Left:</label>
                                <input type="number" id="word-left" min="0" max="500" value="270" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Right:</label>
                                <input type="number" id="word-right" min="0" max="500" value="270" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-gray-200">
                            <div class="input-group">
                                <label>Font:</label>
                                <input type="number" id="word-font-size" min="24" max="120" value="72" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Weight:</label>
                                <select id="word-font-weight" class="p-2 border rounded-lg" onchange="update()">
                                    <option value="normal">Normal</option>
                                    <option value="bold" selected>Bold</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Definition -->
                <div class="card">
                    <div class="section-title"><i class="fas fa-align-left text-blue-500"></i> Definition</div>
                    <div class="element-card">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="input-group">
                                <label>Y:</label>
                                <input type="number" id="def-y" min="0" max="800" value="230" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>H:</label>
                                <input type="number" id="def-h" min="20" max="300" value="75" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-4 mt-3">
                            <div class="input-group">
                                <label>Left:</label>
                                <input type="number" id="def-left" min="0" max="500" value="270" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Right:</label>
                                <input type="number" id="def-right" min="0" max="500" value="270" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-gray-200">
                            <div class="input-group">
                                <label>Font:</label>
                                <input type="number" id="def-font-size" min="16" max="72" value="36" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Wt:</label>
                                <select id="def-font-weight" class="p-2 border rounded-lg text-sm" onchange="update()">
                                    <option value="normal" selected>Normal</option>
                                    <option value="bold">Bold</option>
                                </select>
                            </div>
                            <div class="input-group">
                                <label>Line:</label>
                                <input type="number" id="def-line-spacing" min="1.0" max="3.0" step="0.1" value="1.2" onchange="update()">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Image -->
                <div class="card">
                    <div class="section-title"><i class="fas fa-image text-green-500"></i> Image</div>
                    <div class="element-card">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="input-group">
                                <label>Y:</label>
                                <input type="number" id="img-y" min="0" max="1500" value="305" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>H:</label>
                                <input type="number" id="img-h" min="50" max="600" value="225" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-4 mt-3">
                            <div class="input-group">
                                <label>Left:</label>
                                <input type="number" id="img-left" min="0" max="500" value="163" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Right:</label>
                                <input type="number" id="img-right" min="0" max="500" value="167" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="grid grid-cols-1 gap-4 mt-3">
                            <div class="input-group">
                                <label>Max W:</label>
                                <input type="number" id="img-w" min="100" max="1000" value="750" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Branding -->
                <div class="card">
                    <div class="section-title"><i class="fas fa-at text-orange-500"></i> Branding</div>
                    <div class="element-card">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="input-group">
                                <label>Y:</label>
                                <input type="number" id="brand-y" min="0" max="1800" value="540" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>H:</label>
                                <input type="number" id="brand-h" min="10" max="100" value="30" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-4 mt-3">
                            <div class="input-group">
                                <label>Left:</label>
                                <input type="number" id="brand-left" min="0" max="500" value="270" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Right:</label>
                                <input type="number" id="brand-right" min="0" max="500" value="270" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="mt-3">
                            <label class="block text-sm text-gray-600 mb-1">Channel Name:</label>
                            <input type="text" id="channel-name" value="@WhiteEnglishVocabulary" class="w-full p-2 border rounded-lg" onchange="update()">
                        </div>
                    </div>
                </div>
                
                <!-- Global Safe Area (Reference) -->
                <div class="card">
                    <div class="section-title"><i class="fas fa-border-style text-red-500"></i> Global Safe Area (Reference)</div>
                    <div class="element-card">
                        <p class="text-xs text-gray-500 mb-3">Legacy global safe area. Each component now has individual Left/Right margins above.</p>
                        <div class="grid grid-cols-3 gap-4">
                            <div class="input-group">
                                <label>Left:</label>
                                <input type="number" id="safe-left" min="0" max="500" value="270" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Right:</label>
                                <input type="number" id="safe-right" min="500" max="1080" value="810" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Width:</label>
                                <span id="safe-width" class="font-bold text-purple-600">540</span>
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Action Buttons -->
                <div class="flex gap-4">
                    <button onclick="saveAndApply()" class="btn btn-success flex-1">
                        <i class="fas fa-check"></i> Save & Apply
                    </button>
                    <button onclick="resetToDefault()" class="btn btn-secondary">
                        <i class="fas fa-undo"></i> Reset
                    </button>
                </div>
            </div>
            
            <!-- Preview Panel -->
            <div class="lg:col-span-1">
                <div class="card sticky top-6">
                    <div class="section-title"><i class="fas fa-eye text-indigo-500"></i> Live Preview</div>
                    
                    <!-- Preview Text Controls -->
                    <div class="mb-4 space-y-2">
                        <div>
                            <label class="block text-xs font-semibold text-gray-500 mb-1">Preview Word:</label>
                            <input type="text" id="preview-word" value="Dissolve" 
                                   class="w-full p-2 text-sm border rounded-lg" onchange="update()" oninput="update()" placeholder="Enter word...">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-gray-500 mb-1">Preview Definition:</label>
                            <textarea id="preview-definition" rows="2" 
                                      class="w-full p-2 text-sm border rounded-lg" onchange="update()" oninput="update()" 
                                      placeholder="Enter definition...">To break up or stop working together as a group</textarea>
                        </div>
                    </div>
                    
                    <div id="preview" class="preview-box">
                        <!-- Preview content rendered by JS -->
                    </div>
                    <div class="specs-panel">
                        <table>
                            <tr><td>Canvas:</td><td>1080 × 1920 px</td></tr>
                            <tr><td>Aspect:</td><td>9:16 (Vertical)</td></tr>
                            <tr><td>Scale:</td><td>1:4 (preview)</td></tr>
                        </table>
                    </div>
                    <button onclick="generatePreview()" class="btn btn-primary w-full mt-4">
                        <i class="fas fa-image"></i> Generate Server Preview
                    </button>
                </div>
            </div>
        </div>
    </main>
    
    <div id="toast" class="toast"><i class="fas fa-check-circle mr-2"></i><span id="toast-msg"></span></div>
    
    <script>
        let config = null;
        const SCALE = 4; // 1080/270 = 4, preview is 1/4 scale
        const DEFAULT_CONFIG = {
            elements: {
                word_title: { y_start: 175, y_end: 230, height: 55, left_margin: 270, right_margin: 270 },
                definition: { y_start: 230, y_end: 305, height: 75, left_margin: 270, right_margin: 270 },
                image: { y_start: 305, y_end: 530, height: 225, max_width: 750, left_margin: 163, right_margin: 167 },
                branding: { y_start: 540, y_end: 570, height: 30, left_margin: 270, right_margin: 270 }
            },
            safe_area: { left: 270, right: 810, width: 540 },
            branding: { channel_name: "@WhiteEnglishVocabulary" }
        };
        
        async function loadConfig() {
            try {
                const res = await fetch('/api/layout/config');
                config = await res.json();
                applyConfigToUI();
                update();
            } catch (e) {
                showToast('Failed to load config: ' + e.message, 'error');
            }
        }
        
        function applyConfigToUI() {
            if (!config) return;
            
            // Word
            document.getElementById('word-y').value = config.elements.word_title.y_start || 175;
            document.getElementById('word-h').value = config.elements.word_title.height || 55;
            document.getElementById('word-left').value = config.elements.word_title.left_margin || 270;
            document.getElementById('word-right').value = config.elements.word_title.right_margin || 270;
            document.getElementById('word-font-size').value = config.elements.word_title.font_size || 72;
            document.getElementById('word-font-weight').value = config.elements.word_title.font_weight || 'bold';
            
            // Definition
            document.getElementById('def-y').value = config.elements.definition.y_start || 230;
            document.getElementById('def-h').value = config.elements.definition.height || 75;
            document.getElementById('def-left').value = config.elements.definition.left_margin || 270;
            document.getElementById('def-right').value = config.elements.definition.right_margin || 270;
            document.getElementById('def-font-size').value = config.elements.definition.font_size || 36;
            document.getElementById('def-font-weight').value = config.elements.definition.font_weight || 'normal';
            document.getElementById('def-line-spacing').value = config.elements.definition.line_spacing || 1.2;
            
            // Image
            document.getElementById('img-y').value = config.elements.image.y_start || 305;
            document.getElementById('img-h').value = config.elements.image.height || 225;
            document.getElementById('img-w').value = config.elements.image.max_width || 750;
            document.getElementById('img-left').value = config.elements.image.left_margin || 163;
            document.getElementById('img-right').value = config.elements.image.right_margin || 167;
            
            // Branding
            document.getElementById('brand-y').value = config.elements.branding.y_start || 540;
            document.getElementById('brand-h').value = config.elements.branding.height || 30;
            document.getElementById('brand-left').value = config.elements.branding.left_margin || 270;
            document.getElementById('brand-right').value = config.elements.branding.right_margin || 270;
            document.getElementById('channel-name').value = config.branding?.channel_name || "@WhiteEnglishVocabulary";
            
            // Safe Area
            document.getElementById('safe-left').value = config.safe_area.left || 270;
            document.getElementById('safe-right').value = config.safe_area.right || 810;
        }
        
        function getUIValues() {
            return {
                word: {
                    y: parseInt(document.getElementById('word-y').value),
                    h: parseInt(document.getElementById('word-h').value),
                    left: parseInt(document.getElementById('word-left').value),
                    right: parseInt(document.getElementById('word-right').value),
                    fontSize: parseInt(document.getElementById('word-font-size').value),
                    fontWeight: document.getElementById('word-font-weight').value
                },
                def: {
                    y: parseInt(document.getElementById('def-y').value),
                    h: parseInt(document.getElementById('def-h').value),
                    left: parseInt(document.getElementById('def-left').value),
                    right: parseInt(document.getElementById('def-right').value),
                    fontSize: parseInt(document.getElementById('def-font-size').value),
                    fontWeight: document.getElementById('def-font-weight').value,
                    lineSpacing: parseFloat(document.getElementById('def-line-spacing').value)
                },
                img: {
                    y: parseInt(document.getElementById('img-y').value),
                    h: parseInt(document.getElementById('img-h').value),
                    w: parseInt(document.getElementById('img-w').value),
                    left: parseInt(document.getElementById('img-left').value),
                    right: parseInt(document.getElementById('img-right').value)
                },
                brand: {
                    y: parseInt(document.getElementById('brand-y').value),
                    h: parseInt(document.getElementById('brand-h').value),
                    left: parseInt(document.getElementById('brand-left').value),
                    right: parseInt(document.getElementById('brand-right').value)
                },
                safe: {
                    left: parseInt(document.getElementById('safe-left').value),
                    right: parseInt(document.getElementById('safe-right').value)
                },
                channelName: document.getElementById('channel-name').value,
                previewWord: document.getElementById('preview-word').value || 'Dissolve',
                previewDefinition: document.getElementById('preview-definition').value || 'To break up or stop working together as a group'
            };
        }
        
        function update() {
            const v = getUIValues();
            
            // Update safe width display
            const safeWidth = v.safe.right - v.safe.left;
            document.getElementById('safe-width').textContent = safeWidth;
            
            // Scale values for preview (1/4 scale)
            const s = (val) => val / SCALE;
            
            // Calculate individual element widths based on their margins
            const wordWidth = 1080 - v.word.left - v.word.right;
            const defWidth = 1080 - v.def.left - v.def.right;
            const imgWidth = 1080 - v.img.left - v.img.right;
            const brandWidth = 1080 - v.brand.left - v.brand.right;
            
            // Calculate center X for each element
            const wordCenterX = v.word.left + wordWidth / 2;
            const defCenterX = v.def.left + defWidth / 2;
            const imgCenterX = v.img.left + imgWidth / 2;
            const brandCenterX = v.brand.left + brandWidth / 2;
            
            // Build preview HTML
            const previewHTML = `
                <!-- Safe Area (Reference) -->
                <div class="safe-area" style="left:${s(v.safe.left)}px;right:${s(1080-v.safe.right)}px;top:0;bottom:0;"></div>
                
                <!-- Guide Lines -->
                <div class="guide-line" style="top:${s(v.word.y)}px;" data-label="${v.word.y}"></div>
                <div class="guide-line" style="top:${s(v.word.y + v.word.h)}px;"></div>
                <div class="guide-line" style="top:${s(v.def.y + v.def.h)}px;background:rgba(59,130,246,0.5);"></div>
                <div class="guide-line" style="top:${s(v.img.y)}px;background:rgba(16,185,129,0.5);"></div>
                <div class="guide-line" style="top:${s(v.img.y + v.img.h)}px;background:rgba(16,185,129,0.5);"></div>
                <div class="guide-line" style="top:${s(v.brand.y)}px;background:rgba(249,115,22,0.5);"></div>
                
                <!-- Word -->
                <div class="element-preview" style="top:${s(v.word.y)}px;left:${s(v.word.left)}px;width:${s(wordWidth)}px;height:${s(v.word.h)}px;font-size:${s(v.word.fontSize)}px;font-weight:${v.word.fontWeight};line-height:${s(v.word.h)}px;color:#232323;">
                    ${v.previewWord}
                </div>
                
                <!-- Definition -->
                <div class="element-preview" style="top:${s(v.def.y)}px;left:${s(v.def.left)}px;width:${s(defWidth)}px;height:${s(v.def.h)}px;font-size:${s(v.def.fontSize)}px;font-weight:${v.def.fontWeight};line-height:${v.def.lineSpacing};color:#3c3c3c;overflow:hidden;">
                    ${v.previewDefinition}
                </div>
                
                <!-- Image Placeholder -->
                <div class="element-preview" style="top:${s(v.img.y)}px;left:${s(v.img.left)}px;width:${s(imgWidth)}px;height:${s(v.img.h)}px;display:flex;align-items:center;justify-content:center;">
                    <div style="width:${s(180)}px;height:${s(180)}px;border:2px dashed #ccc;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#999;font-size:10px;">
                        [IMAGE]
                    </div>
                </div>
                
                <!-- Branding -->
                <div class="element-preview" style="top:${s(v.brand.y)}px;left:${s(v.brand.left)}px;width:${s(brandWidth)}px;height:${s(v.brand.h)}px;font-size:${s(28)}px;color:#646464;line-height:${s(v.brand.h)}px;">
                    ${v.channelName}
                </div>
            `;
            
            document.getElementById('preview').innerHTML = previewHTML;
        }
        
        function applyUIToConfig() {
            if (!config) return;
            
            const v = getUIValues();
            
            // Word
            config.elements.word_title.y_start = v.word.y;
            config.elements.word_title.y_end = v.word.y + v.word.h;
            config.elements.word_title.height = v.word.h;
            config.elements.word_title.left_margin = v.word.left;
            config.elements.word_title.right_margin = v.word.right;
            config.elements.word_title.font_size = v.word.fontSize;
            config.elements.word_title.font_weight = v.word.fontWeight;
            
            // Definition
            config.elements.definition.y_start = v.def.y;
            config.elements.definition.y_end = v.def.y + v.def.h;
            config.elements.definition.height = v.def.h;
            config.elements.definition.left_margin = v.def.left;
            config.elements.definition.right_margin = v.def.right;
            config.elements.definition.font_size = v.def.fontSize;
            config.elements.definition.font_weight = v.def.fontWeight;
            config.elements.definition.line_spacing = v.def.lineSpacing;
            
            // Image
            config.elements.image.y_start = v.img.y;
            config.elements.image.y_end = v.img.y + v.img.h;
            config.elements.image.height = v.img.h;
            config.elements.image.max_width = v.img.w;
            config.elements.image.left_margin = v.img.left;
            config.elements.image.right_margin = v.img.right;
            // Keep x_offset in sync with left_margin for backward compatibility
            config.elements.image.x_offset = v.img.left;
            
            // Branding
            config.elements.branding.y_start = v.brand.y;
            config.elements.branding.y_end = v.brand.y + v.brand.h;
            config.elements.branding.height = v.brand.h;
            config.elements.branding.left_margin = v.brand.left;
            config.elements.branding.right_margin = v.brand.right;
            // Keep x_offset in sync with left_margin for backward compatibility
            config.elements.branding.x_offset = v.brand.left;
            
            // Safe Area
            config.safe_area.left = v.safe.left;
            config.safe_area.right = v.safe.right;
            config.safe_area.width = v.safe.right - v.safe.left;
            
            // Branding text
            config.branding = config.branding || {};
            config.branding.channel_name = v.channelName;
        }
        
        async function saveAndApply() {
            applyUIToConfig();
            
            try {
                // Save config
                const saveRes = await fetch('/api/layout/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(config)
                });
                const saveResult = await saveRes.json();
                
                if (!saveResult.success) {
                    throw new Error(saveResult.error || 'Save failed');
                }
                
                // Reload config in backend to apply changes
                const reloadRes = await fetch('/api/layout/config/reload', { method: 'POST' });
                const reloadResult = await reloadRes.json();
                
                if (!reloadResult.success) {
                    throw new Error(reloadResult.error || 'Reload failed');
                }
                
                showToast('Configuration saved and applied!', 'success');
            } catch (e) {
                showToast('Error: ' + e.message, 'error');
            }
        }
        
        async function reloadConfig() {
            try {
                // First reload from file on backend
                await fetch('/api/layout/config/reload', { method: 'POST' });
                // Then reload in UI
                await loadConfig();
                showToast('Configuration reloaded from file', 'success');
            } catch (e) {
                showToast('Error: ' + e.message, 'error');
            }
        }
        
        function downloadConfig() {
            applyUIToConfig();
            const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'layout_config.json';
            a.click();
            URL.revokeObjectURL(url);
            showToast('Configuration downloaded', 'success');
        }
        
        function importConfig(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    config = JSON.parse(e.target.result);
                    applyConfigToUI();
                    update();
                    showToast('Configuration imported. Click Save & Apply to apply.', 'success');
                } catch (err) {
                    showToast('Invalid JSON file: ' + err.message, 'error');
                }
            };
            reader.readAsText(file);
            event.target.value = ''; // Reset file input
        }
        
        function resetToDefault() {
            if (!confirm('Reset all values to default?')) return;
            
            // Apply defaults
            document.getElementById('word-y').value = 175;
            document.getElementById('word-h').value = 55;
            document.getElementById('word-left').value = 270;
            document.getElementById('word-right').value = 270;
            document.getElementById('word-font-size').value = 72;
            document.getElementById('word-font-weight').value = 'bold';
            document.getElementById('def-y').value = 230;
            document.getElementById('def-h').value = 75;
            document.getElementById('def-left').value = 270;
            document.getElementById('def-right').value = 270;
            document.getElementById('def-font-size').value = 36;
            document.getElementById('def-font-weight').value = 'normal';
            document.getElementById('def-line-spacing').value = 1.2;
            document.getElementById('img-y').value = 305;
            document.getElementById('img-h').value = 225;
            document.getElementById('img-w').value = 750;
            document.getElementById('img-left').value = 163;
            document.getElementById('img-right').value = 167;
            document.getElementById('brand-y').value = 540;
            document.getElementById('brand-h').value = 30;
            document.getElementById('brand-left').value = 270;
            document.getElementById('brand-right').value = 270;
            document.getElementById('safe-left').value = 270;
            document.getElementById('safe-right').value = 810;
            document.getElementById('channel-name').value = '@WhiteEnglishVocabulary';
            
            update();
            showToast('Reset to defaults. Click Save & Apply to apply.', 'success');
        }
        
        async function generatePreview() {
            const v = getUIValues();
            try {
                const res = await fetch('/api/preview/layout', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ word: v.previewWord, definition: v.previewDefinition, show_guides: true })
                });
                const result = await res.json();
                if (result.success) {
                    window.open(result.preview_url, '_blank');
                    showToast('Preview generated!', 'success');
                } else {
                    throw new Error(result.error);
                }
            } catch (e) {
                showToast('Error: ' + e.message, 'error');
            }
        }
        
        function showToast(msg, type = 'success') {
            const toast = document.getElementById('toast');
            const toastMsg = document.getElementById('toast-msg');
            toast.className = 'toast ' + type;
            toastMsg.textContent = msg;
            toast.style.display = 'block';
            setTimeout(() => toast.style.display = 'none', 4000);
        }
        
        // Initialize
        window.addEventListener('DOMContentLoaded', loadConfig);
    </script>
</body>
</html>
'''

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    """Serve the web UI."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/output/<path:filename>')
def serve_output(filename):
    """Serve files from output directory."""
    return send_from_directory(config.OUTPUT_DIR, filename)


# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint for Docker."""
    return jsonify({"status": "healthy", "service": "vocab-reels-generator"})


@app.route('/api/version', methods=['GET'])
def api_version():
    """Get current version info."""
    version_file = config.BASE_DIR / "version_info.json"
    
    if version_file.exists():
        import json
        with open(version_file, 'r') as f:
            return jsonify(json.load(f))
    
    # Default fallback
    return jsonify({
        "version": "dev",
        "branch": "unknown",
        "commit": "local",
        "description": "Version info not available"
    })


@app.route('/api/status', methods=['GET'])
def api_status():
    """Check all services status."""
    return jsonify(generator.check_services())


@app.route('/api/words', methods=['GET'])
def api_list_words():
    """List all vocabulary words."""
    return jsonify(get_all_words())


@app.route('/api/words', methods=['POST'])
def api_add_word():
    """Add a new word."""
    data = request.get_json() or request.form
    
    word = data.get('word')
    definition = data.get('definition')
    example = data.get('example', '')
    prompt_image_guideline = data.get('prompt_image_guideline', '')
    
    if not word or not definition:
        return jsonify({"error": "word and definition are required"}), 400
    
    index = add_word(word, definition, example, prompt_image_guideline)
    return jsonify({"success": True, "index": index, "word": word})


@app.route('/api/words/<int:index>', methods=['DELETE'])
def api_delete_word(index):
    """Delete a word."""
    if delete_word(index):
        return jsonify({"success": True})
    return jsonify({"error": "Word not found"}), 404


@app.route('/api/words/clear', methods=['DELETE'])
def api_clear_words():
    """Clear all words."""
    words = get_all_words()
    count = len(words)
    clear_all_words()
    return jsonify({"success": True, "deleted_count": count})


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """Generate a video for a word."""
    # Handle both JSON and form data (for file uploads)
    if request.content_type and 'multipart/form-data' in request.content_type:
        word = request.form.get('word')
        definition = request.form.get('definition')
        example = request.form.get('example', '')
        prompt_image_guideline = request.form.get('prompt_image_guideline', '')
        vocabulary_type = request.form.get('vocabulary_type', 'GeneralEnglish')
        revision = int(request.form.get('revision', 1))
        target_revision = int(request.form.get('target_revision', 5))
        
        # Handle custom image upload
        custom_image_path = None
        if 'custom_image' in request.files:
            file = request.files['custom_image']
            if file and file.filename and allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif', 'webp'}):
                filename = secure_filename(file.filename)
                custom_image_path = config.UPLOADS_DIR / filename
                file.save(custom_image_path)
    else:
        data = request.get_json() or {}
        word = data.get('word')
        definition = data.get('definition')
        example = data.get('example', '')
        prompt_image_guideline = data.get('prompt_image_guideline', '')
        vocabulary_type = data.get('vocabulary_type', 'GeneralEnglish')
        revision = int(data.get('revision', 1))
        target_revision = int(data.get('target_revision', 5))
        custom_image_path = data.get('custom_image_path')
    
    if not word or not definition:
        return jsonify({"error": "word and definition are required"}), 400
    
    result = generator.generate_video(
        word=word, 
        definition=definition, 
        example=example,
        prompt_image_guideline=prompt_image_guideline,
        custom_image_path=custom_image_path,
        vocabulary_type=vocabulary_type,
        revision=revision,
        target_revision=target_revision
    )
    return jsonify(result)


@app.route('/api/generate/<int:index>', methods=['POST'])
def api_generate_by_index(index):
    """Generate video for a word by its index."""
    word_data = get_word_by_index(index)
    if not word_data:
        return jsonify({"error": "Word not found"}), 404
    
    result = generator.generate_video(
        word_data['word'],
        word_data['definition'],
        word_data.get('example', ''),
        prompt_image_guideline=word_data.get('prompt_image_guideline', ''),
        word_index=index,
        vocabulary_type=word_data.get('vocabulary_type', 'GeneralEnglish'),
        revision=word_data.get('revision', 1),
        target_revision=word_data.get('target_revision', 5)
    )
    return jsonify(result)


@app.route('/api/generate/image', methods=['POST'])
def api_generate_image():
    """Generate only the image (for preview)."""
    data = request.get_json() or {}
    word = data.get('word')
    definition = data.get('definition')
    
    if not word or not definition:
        return jsonify({"error": "word and definition are required"}), 400
    
    return jsonify(generator.generate_image_only(word, definition))


@app.route('/api/generate/audio', methods=['POST'])
def api_generate_audio():
    """Generate only the audio (for preview)."""
    data = request.get_json() or {}
    word = data.get('word')
    definition = data.get('definition')
    example = data.get('example', '')
    
    if not word or not definition:
        return jsonify({"error": "word and definition are required"}), 400
    
    return jsonify(generator.generate_audio_only(word, definition, example))


@app.route('/api/generate/batch', methods=['POST'])
def api_generate_batch():
    """Generate videos for all pending words."""
    words = get_all_words()
    pending = [w for w in words if w['status'] == 'pending']
    
    if not pending:
        return jsonify({"success_count": 0, "fail_count": 0, "total": 0, "message": "No pending words"})
    
    success_count = 0
    fail_count = 0
    results = []
    
    for word_data in pending:
        result = generator.generate_video(
            word_data['word'],
            word_data['definition'],
            word_data.get('example', ''),
            prompt_image_guideline=word_data.get('prompt_image_guideline', ''),
            word_index=word_data['index']
        )
        results.append(result)
        
        if result.get('success'):
            success_count += 1
        else:
            fail_count += 1
    
    # Extract successfully generated file names
    generated_files = []
    for r in results:
        if r.get('success') and r.get('video_path'):
            from pathlib import Path
            generated_files.append(Path(r['video_path']).name)
    
    return jsonify({
        "success_count": success_count,
        "fail_count": fail_count,
        "total": len(pending),
        "results": results,
        "generated_files": generated_files
    })


@app.route('/api/upload/csv', methods=['POST'])
def api_upload_csv():
    """Upload a CSV file with vocabulary."""
    if 'csv_file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['csv_file']
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename, {'csv'}):
        return jsonify({"error": "Only CSV files allowed"}), 400
    
    try:
        import pandas as pd
        import io
        
        content = file.read().decode('utf-8')
        df = pd.read_csv(io.StringIO(content))
        
        # Validate columns
        if 'word' not in df.columns or 'definition' not in df.columns:
            return jsonify({"error": "CSV must have 'word' and 'definition' columns"}), 400
        
        # Add missing columns
        if 'example' not in df.columns:
            df['example'] = ''
        if 'status' not in df.columns:
            df['status'] = 'pending'
        if 'video_path' not in df.columns:
            df['video_path'] = ''
        
        # Fill NaN
        df = df.fillna('')
        
        # Save
        save_vocabulary(df)
        
        return jsonify({"success": True, "count": len(df)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/upload/image', methods=['POST'])
def api_upload_image():
    """Upload a custom image."""
    if 'image' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['image']
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif', 'webp'}):
        return jsonify({"error": "Only image files allowed"}), 400
    
    filename = secure_filename(file.filename)
    filepath = config.UPLOADS_DIR / filename
    file.save(filepath)
    
    return jsonify({"success": True, "filename": filename, "path": str(filepath)})


@app.route('/api/download/<filename>')
def api_download(filename):
    """Download a generated file."""
    filepath = config.OUTPUT_DIR / secure_filename(filename)
    if filepath.exists():
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "File not found"}), 404


@app.route('/api/files', methods=['GET'])
def api_list_files():
    """List all output files."""
    files = []
    if config.OUTPUT_DIR.exists():
        for f in config.OUTPUT_DIR.iterdir():
            if f.is_file():
                files.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "type": f.suffix
                })
    return jsonify(sorted(files, key=lambda x: x['name'], reverse=True))


@app.route('/api/files/clear', methods=['DELETE'])
def api_clear_files():
    """Delete all files in the output folder."""
    deleted_count = 0
    errors = []
    
    if config.OUTPUT_DIR.exists():
        for f in config.OUTPUT_DIR.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"{f.name}: {str(e)}")
    
    return jsonify({
        "success": len(errors) == 0,
        "deleted_count": deleted_count,
        "errors": errors
    })


# ============================================
# LAYOUT EDITOR UI
# ============================================

@app.route('/editor')
@app.route('/layout-editor')
def layout_editor():
    """Serve the layout editor interface."""
    return render_template_string(LAYOUT_EDITOR_HTML)


# ============================================
# IMAGE GENERATOR UI
# ============================================

IMAGE_GENERATOR_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Generator - Vocabulary Reels</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .loading-spinner { border: 3px solid #f3f3f3; border-top: 3px solid #10b981; border-radius: 50%; width: 24px; height: 24px; animation: spin 1s linear infinite; display: inline-block; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Header -->
    <header class="gradient-bg text-white py-6 shadow-lg">
        <div class="container mx-auto px-6">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                    <a href="/" class="text-white/80 hover:text-white transition">
                        <i class="fas fa-arrow-left text-xl"></i>
                    </a>
                    <div>
                        <h1 class="text-2xl font-bold flex items-center gap-2">
                            <i class="fas fa-image"></i>
                            Image Generator
                        </h1>
                        <p class="text-green-200 text-sm">Generate AI images with ComfyUI</p>
                    </div>
                </div>
                <div class="flex gap-3">
                    <a href="/layout-editor" class="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition flex items-center gap-2">
                        <i class="fas fa-sliders-h"></i>
                        Layout Editor
                    </a>
                    <a href="/" class="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition flex items-center gap-2">
                        <i class="fas fa-home"></i>
                        Home
                    </a>
                </div>
            </div>
        </div>
    </header>

    <main class="container mx-auto px-6 py-8">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Left: Controls -->
            <div class="space-y-6">
                <!-- Prompt Input -->
                <div class="card p-6">
                    <h2 class="text-lg font-bold mb-4 flex items-center gap-2">
                        <i class="fas fa-pen text-green-600"></i>
                        Prompt Settings
                    </h2>
                    
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">
                                <i class="fas fa-plus-circle text-green-500 mr-1"></i>
                                Positive Prompt
                            </label>
                            <textarea id="positive-prompt" rows="5"
                                      class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 font-mono text-sm"
                                      placeholder="Describe what you want to see..."></textarea>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">
                                <i class="fas fa-minus-circle text-red-500 mr-1"></i>
                                Negative Prompt
                            </label>
                            <textarea id="negative-prompt" rows="3"
                                      class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 font-mono text-sm"
                                      placeholder="Describe what you don't want..."></textarea>
                        </div>
                    </div>
                </div>
                
                <!-- Generation Settings -->
                <div class="card p-6">
                    <h2 class="text-lg font-bold mb-4 flex items-center gap-2">
                        <i class="fas fa-cog text-gray-600"></i>
                        Generation Settings
                    </h2>
                    
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Width</label>
                            <input type="number" id="width" value="1024" 
                                   class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Height</label>
                            <input type="number" id="height" value="1024" 
                                   class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Steps</label>
                            <input type="number" id="steps" value="4" min="1" max="50"
                                   class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">CFG Scale</label>
                            <input type="number" id="cfg" value="2" min="1" max="20" step="0.5"
                                   class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Seed</label>
                            <input type="number" id="seed" value="-1" 
                                   class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500">
                            <p class="text-xs text-gray-400 mt-1">-1 = random</p>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">Sampler</label>
                            <select id="sampler" class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500">
                                <option value="euler_ancestral">Euler Ancestral</option>
                                <option value="euler">Euler</option>
                                <option value="dpmpp_2m">DPM++ 2M</option>
                                <option value="dpmpp_sde">DPM++ SDE</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="mt-4">
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" id="remove-bg" checked 
                                   class="w-5 h-5 text-green-600 rounded focus:ring-green-500">
                            <span class="text-sm font-medium text-gray-700">Remove Background (Transparent PNG)</span>
                        </label>
                    </div>
                    
                    <button onclick="generateImage()" id="generate-btn"
                            class="w-full mt-6 bg-gradient-to-r from-green-500 to-emerald-600 text-white py-3 px-6 rounded-xl font-semibold hover:from-green-600 hover:to-emerald-700 transition flex items-center justify-center gap-2">
                        <i class="fas fa-magic"></i>
                        Generate Image
                    </button>
                </div>
                
                <!-- Preset Templates -->
                <div class="card p-6">
                    <h2 class="text-lg font-bold mb-4 flex items-center gap-2">
                        <i class="fas fa-bookmark text-purple-600"></i>
                        Quick Presets
                    </h2>
                    <div class="grid grid-cols-2 gap-3">
                        <button onclick="loadPreset('vocabulary')" class="p-3 border-2 border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition text-left">
                            <div class="font-semibold text-sm">Vocabulary Style</div>
                            <div class="text-xs text-gray-500">Minimalist educational</div>
                        </button>
                        <button onclick="loadPreset('cartoon')" class="p-3 border-2 border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition text-left">
                            <div class="font-semibold text-sm">Cartoon Style</div>
                            <div class="text-xs text-gray-500">Fun colorful illustrations</div>
                        </button>
                        <button onclick="loadPreset('realistic')" class="p-3 border-2 border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition text-left">
                            <div class="font-semibold text-sm">Realistic</div>
                            <div class="text-xs text-gray-500">Photo-realistic images</div>
                        </button>
                        <button onclick="loadPreset('icon')" class="p-3 border-2 border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition text-left">
                            <div class="font-semibold text-sm">Icon Style</div>
                            <div class="text-xs text-gray-500">Simple flat icons</div>
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Right: Preview -->
            <div class="space-y-6">
                <div class="card p-6">
                    <h2 class="text-lg font-bold mb-4 flex items-center gap-2">
                        <i class="fas fa-eye text-blue-600"></i>
                        Generated Image
                    </h2>
                    
                    <div id="image-preview" class="bg-gray-100 rounded-xl min-h-[400px] flex items-center justify-center border-2 border-dashed border-gray-300">
                        <div class="text-center text-gray-400">
                            <i class="fas fa-image text-6xl mb-4"></i>
                            <p>Generated image will appear here</p>
                        </div>
                    </div>
                    
                    <div id="image-actions" class="hidden mt-4 flex gap-3">
                        <a id="download-link" href="#" download class="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg text-center hover:bg-blue-700 transition">
                            <i class="fas fa-download mr-2"></i>Download
                        </a>
                        <button onclick="copyImageUrl()" class="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition">
                            <i class="fas fa-link mr-2"></i>Copy URL
                        </button>
                    </div>
                </div>
                
                <!-- Generation History -->
                <div class="card p-6">
                    <h2 class="text-lg font-bold mb-4 flex items-center gap-2">
                        <i class="fas fa-history text-orange-600"></i>
                        Recent Generations
                    </h2>
                    <div id="history-grid" class="grid grid-cols-4 gap-2">
                        <p class="col-span-4 text-gray-400 text-center py-4">No images generated yet</p>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        let generatedImages = [];
        let currentImageUrl = '';
        
        // Load layout config prompts on page load
        async function loadLayoutPrompts() {
            try {
                const res = await fetch('/api/layout');
                const config = await res.json();
                
                if (config.image_generation) {
                    document.getElementById('positive-prompt').value = config.image_generation.prompt_template || '';
                    document.getElementById('negative-prompt').value = config.image_generation.negative_prompt || '';
                    document.getElementById('steps').value = config.image_generation.steps || 4;
                    document.getElementById('cfg').value = config.image_generation.cfg_scale || 2;
                    document.getElementById('width').value = config.image_generation.width || 1024;
                    document.getElementById('height').value = config.image_generation.height || 1024;
                }
            } catch (e) {
                console.error('Failed to load layout config:', e);
            }
        }
        
        // Generate image
        async function generateImage() {
            const positivePrompt = document.getElementById('positive-prompt').value;
            const negativePrompt = document.getElementById('negative-prompt').value;
            
            if (!positivePrompt.trim()) {
                alert('Please enter a positive prompt');
                return;
            }
            
            const btn = document.getElementById('generate-btn');
            btn.disabled = true;
            btn.innerHTML = '<span class="loading-spinner"></span> Generating...';
            
            document.getElementById('image-preview').innerHTML = `
                <div class="text-center">
                    <div class="loading-spinner mx-auto mb-4" style="width: 48px; height: 48px;"></div>
                    <p class="text-gray-600">Generating image...</p>
                    <p class="text-gray-400 text-sm mt-2">This may take 10-30 seconds</p>
                </div>
            `;
            
            try {
                const res = await fetch('/api/image/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: positivePrompt,
                        negative_prompt: negativePrompt,
                        width: parseInt(document.getElementById('width').value),
                        height: parseInt(document.getElementById('height').value),
                        steps: parseInt(document.getElementById('steps').value),
                        cfg_scale: parseFloat(document.getElementById('cfg').value),
                        seed: parseInt(document.getElementById('seed').value),
                        sampler: document.getElementById('sampler').value,
                        remove_background: document.getElementById('remove-bg').checked
                    })
                });
                
                const data = await res.json();
                
                if (data.success && data.image_url) {
                    currentImageUrl = data.image_url;
                    document.getElementById('image-preview').innerHTML = `
                        <img src="${data.image_url}" alt="Generated image" 
                             class="max-w-full max-h-[500px] rounded-lg shadow-lg" 
                             style="background: repeating-conic-gradient(#f0f0f0 0% 25%, white 0% 50%) 50% / 20px 20px;">
                    `;
                    document.getElementById('image-actions').classList.remove('hidden');
                    document.getElementById('download-link').href = data.image_url;
                    
                    // Add to history
                    generatedImages.unshift(data.image_url);
                    updateHistory();
                } else {
                    document.getElementById('image-preview').innerHTML = `
                        <div class="text-center text-red-500">
                            <i class="fas fa-exclamation-circle text-4xl mb-4"></i>
                            <p>Generation failed</p>
                            <p class="text-sm mt-2">${data.error || 'Unknown error'}</p>
                        </div>
                    `;
                }
            } catch (e) {
                document.getElementById('image-preview').innerHTML = `
                    <div class="text-center text-red-500">
                        <i class="fas fa-exclamation-circle text-4xl mb-4"></i>
                        <p>Generation failed</p>
                        <p class="text-sm mt-2">${e.message}</p>
                    </div>
                `;
            }
            
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i> Generate Image';
        }
        
        function updateHistory() {
            const grid = document.getElementById('history-grid');
            if (generatedImages.length === 0) {
                grid.innerHTML = '<p class="col-span-4 text-gray-400 text-center py-4">No images generated yet</p>';
                return;
            }
            
            grid.innerHTML = generatedImages.slice(0, 8).map(url => `
                <div class="aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-green-500 transition"
                     onclick="showImage('${url}')"
                     style="background: repeating-conic-gradient(#f0f0f0 0% 25%, white 0% 50%) 50% / 10px 10px;">
                    <img src="${url}" alt="Generated" class="w-full h-full object-cover">
                </div>
            `).join('');
        }
        
        function showImage(url) {
            currentImageUrl = url;
            document.getElementById('image-preview').innerHTML = `
                <img src="${url}" alt="Generated image" 
                     class="max-w-full max-h-[500px] rounded-lg shadow-lg"
                     style="background: repeating-conic-gradient(#f0f0f0 0% 25%, white 0% 50%) 50% / 20px 20px;">
            `;
            document.getElementById('image-actions').classList.remove('hidden');
            document.getElementById('download-link').href = url;
        }
        
        function copyImageUrl() {
            navigator.clipboard.writeText(window.location.origin + currentImageUrl);
            alert('Image URL copied!');
        }
        
        // Preset templates
        function loadPreset(preset) {
            const presets = {
                vocabulary: {
                    positive: 'Simple minimalist illustration, clean simple line drawing, muted brown and beige earth tones, simple cartoon characters or objects, solid pure white background, no text no letters no words, centered composition, flat illustration style, warm colors, educational clipart aesthetic, isolated on white',
                    negative: 'text, words, letters, numbers, watermark, signature, complex background, gradient, pattern, dark background, colorful background, photorealistic, 3d render, busy, cluttered, neon, vibrant colors'
                },
                cartoon: {
                    positive: 'Cute cartoon illustration, colorful, playful, rounded shapes, expressive characters, fun and whimsical, childrens book illustration style, vibrant colors, white background',
                    negative: 'realistic, photorealistic, dark, scary, horror, text, words, complex background'
                },
                realistic: {
                    positive: 'Professional photograph, high quality, sharp focus, beautiful lighting, natural colors, studio photography, detailed, 8k resolution',
                    negative: 'cartoon, illustration, drawing, anime, text, watermark, low quality, blurry'
                },
                icon: {
                    positive: 'Simple flat icon, minimal, clean lines, single color, geometric shapes, modern app icon design, white background, centered, vector style',
                    negative: 'realistic, detailed, complex, gradient, 3d, shadow, text, words, busy'
                }
            };
            
            if (presets[preset]) {
                document.getElementById('positive-prompt').value = presets[preset].positive;
                document.getElementById('negative-prompt').value = presets[preset].negative;
            }
        }
        
        // Load prompts on page load
        loadLayoutPrompts();
    </script>
</body>
</html>
'''

# ============================================
# CSV GENERATOR UI
# ============================================

CSV_GENERATOR_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSV Generator - Vocabulary Reels</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .btn-primary { background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); }
        .btn-primary:hover { background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%); }
        .word-tag { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 20px; font-size: 14px; }
        .word-tag .remove { cursor: pointer; color: #ea580c; }
        .word-tag .remove:hover { color: #c2410c; }
        textarea:focus { outline: none; border-color: #f97316; box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1); }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Header -->
    <header class="gradient-bg text-white py-6 shadow-lg">
        <div class="container mx-auto px-6">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                    <a href="/" class="text-white/80 hover:text-white transition">
                        <i class="fas fa-arrow-left"></i>
                    </a>
                    <div>
                        <h1 class="text-2xl font-bold flex items-center gap-3">
                            <i class="fas fa-file-csv"></i>
                            CSV Generator
                        </h1>
                        <p class="text-orange-200 text-sm mt-1">Generate vocabulary CSV from word list</p>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <main class="container mx-auto px-6 py-8">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Input Section -->
            <div class="space-y-6">
                <div class="card p-6">
                    <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                        <i class="fas fa-keyboard text-orange-600"></i>
                        Enter Words
                    </h2>
                    
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">
                                Words (comma separated)
                            </label>
                            <textarea id="words-input" rows="4" 
                                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl transition"
                                placeholder="love, time, life, world, people, happy, success, dream, hope, peace"></textarea>
                            <p class="text-xs text-gray-500 mt-1">Enter words separated by commas</p>
                        </div>
                        
                        <div id="word-tags" class="flex flex-wrap gap-2 min-h-[40px]"></div>
                        
                        <div class="flex gap-3">
                            <button onclick="parseWords()" class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-3 px-4 rounded-xl transition">
                                <i class="fas fa-tags mr-2"></i>Parse Words
                            </button>
                            <button onclick="clearWords()" class="bg-red-100 hover:bg-red-200 text-red-700 font-semibold py-3 px-4 rounded-xl transition">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="card p-6">
                    <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                        <i class="fas fa-cog text-orange-600"></i>
                        Options
                    </h2>
                    
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Filename</label>
                            <input type="text" id="filename" value="vocabulary_words" 
                                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 transition">
                        </div>
                        
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">
                                <i class="fas fa-tag mr-1"></i>Vocabulary Type
                            </label>
                            <select id="csv-vocabulary-type" class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 transition">
                                <option value="GeneralEnglish" selected>General English</option>
                                <option value="BusinessEnglish">Business English</option>
                                <option value="AcademicEnglish">Academic English</option>
                                <option value="IELTS">IELTS</option>
                                <option value="TOEFL">TOEFL</option>
                            </select>
                        </div>
                        
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="block text-sm font-semibold text-gray-700 mb-2">Starting Revision</label>
                                <input type="number" id="csv-revision" value="1" min="1" max="99"
                                    class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 transition">
                            </div>
                            <div>
                                <label class="block text-sm font-semibold text-gray-700 mb-2">Target Revision</label>
                                <input type="number" id="csv-target-revision" value="5" min="1" max="99"
                                    class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 transition">
                            </div>
                        </div>
                        
                        <div class="flex items-center gap-3">
                            <input type="checkbox" id="include-examples" checked class="w-5 h-5 rounded text-orange-600">
                            <label for="include-examples" class="text-sm text-gray-700">Include example sentences</label>
                        </div>
                        
                        <div class="flex items-center gap-3">
                            <input type="checkbox" id="include-prompts" checked class="w-5 h-5 rounded text-orange-600">
                            <label for="include-prompts" class="text-sm text-gray-700">Include image prompt guidelines</label>
                        </div>
                    </div>
                </div>
                
                <button onclick="generateCSV()" id="generate-btn" 
                    class="w-full btn-primary text-white font-bold py-4 px-6 rounded-xl shadow-lg hover:shadow-xl transition transform hover:-translate-y-0.5">
                    <i class="fas fa-magic mr-2"></i>Generate CSV
                </button>
            </div>
            
            <!-- Preview Section -->
            <div class="space-y-6">
                <div class="card p-6">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-xl font-bold flex items-center gap-2">
                            <i class="fas fa-table text-orange-600"></i>
                            CSV Preview
                        </h2>
                        <span id="word-count" class="text-sm text-gray-500">0 words</span>
                    </div>
                    
                    <div id="csv-preview" class="bg-gray-50 rounded-xl p-4 min-h-[300px] max-h-[500px] overflow-auto">
                        <p class="text-gray-400 text-center py-8">Enter words and click "Generate CSV" to preview</p>
                    </div>
                </div>
                
                <div id="download-section" class="hidden">
                    <div class="card p-6">
                        <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                            <i class="fas fa-download text-green-600"></i>
                            Download
                        </h2>
                        
                        <div class="flex gap-3">
                            <button onclick="downloadCSV()" class="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-xl transition">
                                <i class="fas fa-file-download mr-2"></i>Download CSV
                            </button>
                            <button onclick="loadToDatabase()" class="flex-1 bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 px-4 rounded-xl transition">
                                <i class="fas fa-database mr-2"></i>Load to Database
                            </button>
                        </div>
                    </div>
                </div>
                
                <div id="status-message" class="hidden card p-4">
                    <div class="flex items-center gap-3">
                        <div id="status-icon"></div>
                        <span id="status-text"></span>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        let parsedWords = [];
        let generatedCSVData = [];
        
        function parseWords() {
            const input = document.getElementById('words-input').value;
            const words = input.split(',')
                .map(w => w.trim())
                .filter(w => w.length > 0)
                .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
            
            // Remove duplicates
            parsedWords = [...new Set(words)];
            renderWordTags();
        }
        
        function renderWordTags() {
            const container = document.getElementById('word-tags');
            container.innerHTML = parsedWords.map((word, idx) => `
                <div class="word-tag">
                    <span>${word}</span>
                    <span class="remove" onclick="removeWord(${idx})"><i class="fas fa-times"></i></span>
                </div>
            `).join('');
            document.getElementById('word-count').textContent = `${parsedWords.length} words`;
        }
        
        function removeWord(idx) {
            parsedWords.splice(idx, 1);
            renderWordTags();
        }
        
        function clearWords() {
            parsedWords = [];
            document.getElementById('words-input').value = '';
            renderWordTags();
            document.getElementById('csv-preview').innerHTML = '<p class="text-gray-400 text-center py-8">Enter words and click "Generate CSV" to preview</p>';
            document.getElementById('download-section').classList.add('hidden');
        }
        
        async function generateCSV() {
            if (parsedWords.length === 0) {
                parseWords();
                if (parsedWords.length === 0) {
                    showStatus('error', 'Please enter some words first');
                    return;
                }
            }
            
            const btn = document.getElementById('generate-btn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Generating...';
            
            showStatus('loading', 'Generating definitions and prompts...');
            
            try {
                const response = await fetch('/api/csv/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        words: parsedWords,
                        include_examples: document.getElementById('include-examples').checked,
                        include_prompts: document.getElementById('include-prompts').checked,
                        vocabulary_type: document.getElementById('csv-vocabulary-type').value,
                        revision: parseInt(document.getElementById('csv-revision').value) || 1,
                        target_revision: parseInt(document.getElementById('csv-target-revision').value) || 5
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    generatedCSVData = data.csv_data;
                    renderCSVPreview(data.csv_data);
                    document.getElementById('download-section').classList.remove('hidden');
                    showStatus('success', `Generated ${data.csv_data.length} vocabulary entries`);
                } else {
                    showStatus('error', data.error || 'Generation failed');
                }
            } catch (e) {
                showStatus('error', 'Failed to generate CSV: ' + e.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-magic mr-2"></i>Generate CSV';
            }
        }
        
        function renderCSVPreview(data) {
            if (!data || data.length === 0) {
                document.getElementById('csv-preview').innerHTML = '<p class="text-gray-400 text-center py-8">No data generated</p>';
                return;
            }
            
            let html = '<table class="w-full text-sm">';
            html += '<thead class="bg-orange-100"><tr>';
            html += '<th class="p-2 text-left font-semibold">Word</th>';
            html += '<th class="p-2 text-left font-semibold">Definition</th>';
            html += '<th class="p-2 text-left font-semibold">Example</th>';
            html += '<th class="p-2 text-left font-semibold">Image Prompt</th>';
            html += '<th class="p-2 text-left font-semibold">Type</th>';
            html += '<th class="p-2 text-left font-semibold">Rev</th>';
            html += '</tr></thead><tbody>';
            
            data.forEach((row, idx) => {
                const bgColor = idx % 2 === 0 ? 'bg-white' : 'bg-gray-50';
                html += `<tr class="${bgColor}">`;
                html += `<td class="p-2 font-semibold text-orange-700">${row.word}</td>`;
                html += `<td class="p-2 text-gray-600 text-xs">${row.definition}</td>`;
                html += `<td class="p-2 text-gray-500 text-xs italic">${row.example}</td>`;
                html += `<td class="p-2 text-gray-500 text-xs">${row.prompt_image_guideline}</td>`;
                html += `<td class="p-2 text-gray-500 text-xs">${row.vocabulary_type || 'GeneralEnglish'}</td>`;
                html += `<td class="p-2 text-gray-500 text-xs">${row.revision || 1}/${row.target_revision || 5}</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            document.getElementById('csv-preview').innerHTML = html;
        }
        
        function downloadCSV() {
            if (generatedCSVData.length === 0) return;
            
            const filename = document.getElementById('filename').value || 'vocabulary_words';
            
            // Build CSV content
            let csv = 'word,definition,example,prompt_image_guideline,vocabulary_type,revision,target_revision\\n';
            generatedCSVData.forEach(row => {
                csv += `${escapeCSV(row.word)},${escapeCSV(row.definition)},${escapeCSV(row.example)},${escapeCSV(row.prompt_image_guideline)},${escapeCSV(row.vocabulary_type)},${row.revision},${row.target_revision}\\n`;
            });
            
            // Download
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename + '.csv';
            a.click();
            URL.revokeObjectURL(url);
            
            showStatus('success', 'CSV file downloaded!');
        }
        
        function escapeCSV(str) {
            if (!str) return '';
            str = String(str);
            if (str.includes(',') || str.includes('"') || str.includes('\\n')) {
                return '"' + str.replace(/"/g, '""') + '"';
            }
            return str;
        }
        
        async function loadToDatabase() {
            if (generatedCSVData.length === 0) return;
            
            showStatus('loading', 'Loading words to database...');
            
            try {
                const response = await fetch('/api/csv/load-to-db', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ words: generatedCSVData })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus('success', `Loaded ${data.count} words to database!`);
                } else {
                    showStatus('error', data.error || 'Failed to load to database');
                }
            } catch (e) {
                showStatus('error', 'Failed to load: ' + e.message);
            }
        }
        
        function showStatus(type, message) {
            const container = document.getElementById('status-message');
            const icon = document.getElementById('status-icon');
            const text = document.getElementById('status-text');
            
            container.classList.remove('hidden');
            
            if (type === 'loading') {
                icon.innerHTML = '<div class="w-6 h-6 border-3 border-orange-500 border-t-transparent rounded-full animate-spin"></div>';
                text.className = 'text-orange-600';
            } else if (type === 'success') {
                icon.innerHTML = '<i class="fas fa-check-circle text-green-500 text-xl"></i>';
                text.className = 'text-green-600';
            } else {
                icon.innerHTML = '<i class="fas fa-exclamation-circle text-red-500 text-xl"></i>';
                text.className = 'text-red-600';
            }
            
            text.textContent = message;
            
            if (type !== 'loading') {
                setTimeout(() => container.classList.add('hidden'), 5000);
            }
        }
        
        // Auto-parse on input
        document.getElementById('words-input').addEventListener('input', function() {
            // Debounce
            clearTimeout(this.parseTimeout);
            this.parseTimeout = setTimeout(parseWords, 500);
        });
    </script>
</body>
</html>
'''

@app.route('/csv-generator')
def csv_generator():
    """Serve the CSV generator interface."""
    return render_template_string(CSV_GENERATOR_HTML)


@app.route('/image-generator')
def image_generator():
    """Serve the image generator interface."""
    return render_template_string(IMAGE_GENERATOR_HTML)


# ============================================
# NEW API ENDPOINTS - Layout Configuration & Preview
# ============================================

@app.route('/api/layout/config', methods=['GET'])
def api_get_layout_config():
    """Get current layout configuration."""
    from src.layout_config import get_layout_config
    layout = get_layout_config()
    return jsonify(layout.to_dict())


@app.route('/api/layout/config', methods=['POST'])
def api_update_layout_config():
    """Update layout configuration."""
    from src.layout_config import get_layout_config
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No configuration provided"}), 400
    
    try:
        layout = get_layout_config()
        layout.save(data)
        return jsonify({"success": True, "message": "Configuration updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/layout/config/reload', methods=['POST'])
def api_reload_layout_config():
    """Reload configuration from file."""
    from src.layout_config import reload_layout_config
    
    try:
        reload_layout_config()
        return jsonify({"success": True, "message": "Configuration reloaded"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/preview/layout', methods=['POST'])
def api_preview_layout():
    """Generate layout preview with sample text."""
    from src.preview_generator import create_preview
    
    data = request.get_json() or {}
    word = data.get('word', 'Serendipity')
    definition = data.get('definition', 'Finding something good by happy chance or accident')
    show_guides = data.get('show_guides', True)
    
    try:
        preview_path = create_preview(word, definition, show_guides=show_guides)
        return jsonify({
            "success": True,
            "preview_filename": preview_path.name,
            "preview_url": f"/output/{preview_path.name}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/fonts/list', methods=['GET'])
def api_list_fonts():
    """List all available fonts (system + uploaded)."""
    fonts = []
    
    # System fonts
    import subprocess
    try:
        result = subprocess.run(['fc-list', ':'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            seen_names = set()
            for line in result.stdout.split('\n'):
                if ':' in line:
                    font_path = line.split(':')[0]
                    font_name = Path(font_path).stem
                    if font_name not in seen_names:
                        fonts.append({
                            "name": font_name,
                            "path": font_path,
                            "type": "system"
                        })
                        seen_names.add(font_name)
    except Exception as e:
        print(f"Error listing fonts: {e}")
    
    # Uploaded fonts
    fonts_dir = config.BASE_DIR / "fonts"
    if fonts_dir.exists():
        for ext in ['*.ttf', '*.otf', '*.woff', '*.woff2']:
            for font_file in fonts_dir.glob(ext):
                fonts.append({
                    "name": font_file.stem,
                    "path": str(font_file),
                    "type": "uploaded"
                })
    
    return jsonify(fonts)


@app.route('/api/fonts/upload', methods=['POST'])
def api_upload_font():
    """Upload custom font file."""
    if 'font_file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['font_file']
    if not file or not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    # Check extension
    allowed = {'.ttf', '.otf', '.woff', '.woff2'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        return jsonify({"error": f"Invalid format. Allowed: {', '.join(allowed)}"}), 400
    
    # Save font
    fonts_dir = config.BASE_DIR / "fonts"
    fonts_dir.mkdir(exist_ok=True)
    
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
    fonts = [
        {"name": "Inter", "category": "sans-serif", "weights": ["400", "600", "700", "800"]},
        {"name": "Poppins", "category": "sans-serif", "weights": ["400", "600", "700", "800"]},
        {"name": "Roboto", "category": "sans-serif", "weights": ["400", "500", "700", "900"]},
        {"name": "Open Sans", "category": "sans-serif", "weights": ["400", "600", "700", "800"]},
        {"name": "Montserrat", "category": "sans-serif", "weights": ["400", "600", "700", "800"]},
        {"name": "Lato", "category": "sans-serif", "weights": ["400", "700", "900"]},
        {"name": "Raleway", "category": "sans-serif", "weights": ["400", "600", "700", "800"]},
        {"name": "Nunito", "category": "sans-serif", "weights": ["400", "600", "700", "800"]},
        {"name": "Ubuntu", "category": "sans-serif", "weights": ["400", "500", "700"]},
        {"name": "Work Sans", "category": "sans-serif", "weights": ["400", "600", "700"]},
    ]
    return jsonify(fonts)


@app.route('/api/preview/download', methods=['POST'])
def api_download_preview():
    """Generate and download preview."""
    from src.preview_generator import create_preview
    from datetime import datetime
    
    data = request.get_json() or {}
    word = data.get('word', 'Preview')
    definition = data.get('definition', 'Layout preview')
    show_guides = data.get('show_guides', False)
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"preview_{timestamp}.png"
        
        preview_path = create_preview(word, definition, output_path, show_guides)
        
        return send_file(
            preview_path,
            as_attachment=True,
            download_name=f"layout_preview_{timestamp}.png"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/image/generate', methods=['POST'])
def api_generate_image_advanced():
    """Generate image with custom prompt (no word/definition required)."""
    from src.comfyui_client import ComfyUIClient
    from datetime import datetime
    
    data = request.get_json() or {}
    
    # Get prompt directly
    prompt = data.get('prompt', '').strip()
    negative_prompt = data.get('negative_prompt', config.IMAGE_NEGATIVE_PROMPT).strip()
    
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    
    # Get optional parameters with defaults
    width = int(data.get('width', 1024))
    height = int(data.get('height', 1024))
    steps = int(data.get('steps', 4))
    cfg_scale = float(data.get('cfg_scale', 2.0))
    seed = int(data.get('seed', -1))
    remove_background = data.get('remove_background', True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = config.OUTPUT_DIR / f"generated_image_{timestamp}.png"
    
    try:
        # Create ComfyUI client and generate image
        client = ComfyUIClient()
        
        if not client.is_server_running():
            return jsonify({"success": False, "error": "ComfyUI server is not running. Please start it first."})
        
        result_path = client.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg_scale,
            seed=seed if seed != -1 else None,
            output_path=output_path
        )
        
        if not result_path or not result_path.exists():
            return jsonify({"success": False, "error": "Image generation failed"})
        
        # Remove background if requested
        if remove_background and result_path.exists():
            try:
                from rembg import remove
                from PIL import Image
                img = Image.open(result_path)
                img_no_bg = remove(img)
                img_no_bg.save(result_path, 'PNG')
            except Exception as e:
                print(f"Background removal failed: {e}")
        
        return jsonify({
            "success": True,
            "image_url": f"/output/{result_path.name}",
            "seed": seed
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ============================================
# CSV GENERATOR API ENDPOINTS
# ============================================

# Simple vocabulary definitions for common words (fallback when no AI available)
VOCABULARY_DATABASE = {
    "love": {
        "definition": "A deep affection or strong feeling of care and attachment toward someone or something",
        "example": "I love spending time with my family",
        "prompt": "A cute simple couple holding hands with a big red heart floating above them showing deep affection and care in minimalist cartoon style"
    },
    "time": {
        "definition": "A continuous progression of events from past to future measured in seconds minutes and hours",
        "example": "Time flies when you are having fun",
        "prompt": "A large elegant hourglass with golden sand flowing down showing the concept of time passing in a simple educational illustration style"
    },
    "life": {
        "definition": "The existence of a living being including experiences and growth from birth to death",
        "example": "Life is full of unexpected surprises",
        "prompt": "A beautiful tree of life with roots at bottom growing upward with leaves and birds showing the journey of growth and existence"
    },
    "world": {
        "definition": "The Earth and all its inhabitants or a particular sphere of activity and experience",
        "example": "Travel opens your eyes to the world",
        "prompt": "A colorful Earth globe with tiny diverse people standing around it holding hands showing global unity and connection"
    },
    "people": {
        "definition": "Human beings collectively or a group of individuals sharing common characteristics",
        "example": "People from different cultures have unique traditions",
        "prompt": "A cheerful group of diverse cartoon people of different ages and backgrounds standing together smiling"
    },
    "happy": {
        "definition": "Feeling or showing pleasure contentment or joy",
        "example": "She felt happy when she received the good news",
        "prompt": "A smiling cartoon face with bright eyes and a big cheerful smile radiating happiness with little stars around"
    },
    "success": {
        "definition": "The accomplishment of an aim or purpose achieving a desired outcome",
        "example": "Hard work is the key to success",
        "prompt": "A person standing on top of a mountain with arms raised in victory celebrating achievement and success"
    },
    "dream": {
        "definition": "A series of images thoughts or sensations occurring in sleep or a cherished aspiration",
        "example": "Follow your dreams and never give up",
        "prompt": "A sleeping person with a thought bubble showing stars clouds and magical imagery representing dreams and aspirations"
    },
    "hope": {
        "definition": "A feeling of expectation and desire for a certain thing to happen",
        "example": "We hope for a better tomorrow",
        "prompt": "A small plant sprouting from the ground with a bright sun rising in the background symbolizing hope and new beginnings"
    },
    "peace": {
        "definition": "Freedom from disturbance or a state of tranquility and calm",
        "example": "Everyone deserves to live in peace",
        "prompt": "A white dove flying with an olive branch in a clear blue sky representing peace and harmony"
    },
    "family": {
        "definition": "A group of people related by blood marriage or adoption living together",
        "example": "Family is the most important thing in life",
        "prompt": "A happy cartoon family with parents and children holding hands in front of a simple house"
    },
    "friend": {
        "definition": "A person with whom one has a bond of mutual affection and trust",
        "example": "A true friend is always there for you",
        "prompt": "Two cartoon friends giving each other a high five with big smiles showing friendship and trust"
    },
    "work": {
        "definition": "Activity involving mental or physical effort done to achieve a purpose or result",
        "example": "Hard work leads to great results",
        "prompt": "A person at a desk working on a laptop with determination showing productivity and effort"
    },
    "home": {
        "definition": "The place where one lives permanently especially as a member of a family",
        "example": "There is no place like home",
        "prompt": "A cozy simple house with smoke coming from chimney and a warm welcoming feel"
    },
    "learn": {
        "definition": "To gain knowledge or skill through study experience or being taught",
        "example": "We learn something new every day",
        "prompt": "A curious student reading a book with a lightbulb appearing above their head showing learning and understanding"
    },
    "help": {
        "definition": "To make it easier for someone to do something by offering assistance",
        "example": "Please help me carry these bags",
        "prompt": "Two people where one is helping the other climb up showing assistance and support"
    },
    "change": {
        "definition": "To make or become different or to transform from one state to another",
        "example": "Change is the only constant in life",
        "prompt": "A caterpillar transforming into a beautiful butterfly showing change and transformation"
    },
    "think": {
        "definition": "To use ones mind to consider or reason about something",
        "example": "Think before you speak",
        "prompt": "A person with hand on chin in thinking pose with thought bubbles and question marks around"
    },
    "feel": {
        "definition": "To experience an emotion or sensation",
        "example": "I feel grateful for everything I have",
        "prompt": "A heart with different emotion symbols around it showing various feelings and emotions"
    },
    "grow": {
        "definition": "To increase in size or develop and mature over time",
        "example": "Children grow up so fast",
        "prompt": "A sequence showing a small seedling growing into a tall strong tree over time"
    },
    # Advanced/Interesting Vocabulary
    "petrichor": {
        "definition": "The pleasant earthy smell produced when rain falls on dry ground",
        "example": "After the storm passed I stepped outside and enjoyed the petrichor",
        "prompt": "Rain drops falling on dry cracked earth with visible steam or mist rising up showing the fresh smell of rain on soil"
    },
    "defenestration": {
        "definition": "The act of throwing someone or something out of a window",
        "example": "The defenestration of the old computer was quite dramatic",
        "prompt": "A cartoon showing an object being thrown out of an open window with motion lines showing the dramatic exit"
    },
    "crepuscular": {
        "definition": "Relating to or resembling twilight occurring or active during twilight",
        "example": "Rabbits are crepuscular animals most active at dawn and dusk",
        "prompt": "A beautiful twilight scene with a setting sun creating orange and purple sky colors with silhouettes of animals"
    },
    "gossamer": {
        "definition": "A fine filmy substance of cobwebs or something extremely light delicate and insubstantial",
        "example": "The gossamer wings of the dragonfly glistened in the sunlight",
        "prompt": "A delicate spider web with morning dew drops glistening in soft light showing fragility and beauty"
    },
    "phosphenes": {
        "definition": "The phenomenon of seeing light without light actually entering the eye such as when pressing on closed eyelids",
        "example": "When I rubbed my tired eyes I saw colorful phosphenes",
        "prompt": "A closed eye with colorful swirling patterns and lights appearing inside representing the visual phenomenon"
    },
    "pareidolia": {
        "definition": "The tendency to perceive meaningful images in random patterns such as seeing faces in clouds",
        "example": "Due to pareidolia the cloud looked exactly like a smiling face",
        "prompt": "A fluffy cloud in the sky that clearly resembles a smiling human face showing pattern recognition"
    },
    "murmuration": {
        "definition": "A large group of starlings flying together in coordinated swirling patterns",
        "example": "We watched the beautiful murmuration of birds at sunset",
        "prompt": "Thousands of small birds flying together forming beautiful swirling wave patterns against an evening sky"
    },
    "ferrule": {
        "definition": "A metal ring or cap placed around a pole or stick to strengthen it or prevent splitting",
        "example": "The ferrule on my umbrella was made of brass",
        "prompt": "A close up of a metal ring cap at the end of an umbrella or walking stick showing the protective metal band"
    },
    "aglet": {
        "definition": "The small plastic or metal sheath at the end of a shoelace that prevents fraying",
        "example": "I need new shoelaces because the aglets have fallen off",
        "prompt": "A close up of a shoelace end showing the small plastic tip that holds the lace together"
    },
    "berm": {
        "definition": "A raised bank or flat strip of land bordering a road canal or other feature",
        "example": "The cyclists rode along the berm beside the highway",
        "prompt": "A raised earthen mound or grassy strip running alongside a road showing the landscape feature"
    },
    "serendipity": {
        "definition": "The occurrence of events by chance in a happy or beneficial way",
        "example": "Meeting my best friend was pure serendipity",
        "prompt": "Two people bumping into each other by accident with happy surprised expressions and sparkles around them"
    },
    "ephemeral": {
        "definition": "Lasting for a very short time fleeting and transient",
        "example": "The beauty of cherry blossoms is ephemeral",
        "prompt": "Cherry blossom petals falling gently from a tree with some fading away showing the temporary nature"
    },
    "mellifluous": {
        "definition": "Having a smooth rich flow of sound that is pleasant to hear",
        "example": "The singer had a mellifluous voice that captivated everyone",
        "prompt": "Musical notes flowing smoothly like honey from a persons mouth showing sweet sounding speech or music"
    },
    "sonder": {
        "definition": "The realization that each passerby has a life as vivid and complex as your own",
        "example": "Walking through the busy street I felt a moment of sonder",
        "prompt": "A crowd of people walking with thought bubbles showing their different complex lives and stories"
    },
    "limerence": {
        "definition": "The state of being infatuated or obsessed with another person involuntarily",
        "example": "His limerence for her made it hard to focus on anything else",
        "prompt": "A person with heart eyes looking dreamily at another person with hearts floating around their head"
    },
    "wanderlust": {
        "definition": "A strong desire to travel and explore the world",
        "example": "Her wanderlust led her to visit over fifty countries",
        "prompt": "A person with a backpack looking at a world map with pins and airplane routes showing travel desire"
    },
    "eloquent": {
        "definition": "Fluent or persuasive in speaking or writing expressing ideas clearly and effectively",
        "example": "The eloquent speaker captivated the entire audience",
        "prompt": "A confident person speaking at a podium with beautiful flowing words and engaged listeners"
    },
    "resilient": {
        "definition": "Able to recover quickly from difficulties or setbacks showing toughness",
        "example": "She proved to be resilient after facing many challenges",
        "prompt": "A small plant growing through a crack in concrete showing strength and ability to overcome obstacles"
    },
    "ubiquitous": {
        "definition": "Present appearing or found everywhere at the same time",
        "example": "Smartphones have become ubiquitous in modern society",
        "prompt": "The same object appearing in multiple places at once showing something that is everywhere"
    },
    "enigma": {
        "definition": "A person or thing that is mysterious puzzling or difficult to understand",
        "example": "The ancient ruins remain an enigma to archaeologists",
        "prompt": "A mysterious figure in shadow with question marks around them showing something puzzling and unknown"
    }
}


def generate_vocabulary_entry(word: str) -> dict:
    """Generate vocabulary entry for a word."""
    word_lower = word.lower().strip()
    
    # Check if word exists in our database
    if word_lower in VOCABULARY_DATABASE:
        entry = VOCABULARY_DATABASE[word_lower]
        return {
            "word": word.strip().title(),
            "definition": entry["definition"],
            "example": entry["example"],
            "prompt_image_guideline": entry["prompt"]
        }
    
    # Generate generic entry for unknown words
    return {
        "word": word.strip().title(),
        "definition": f"The meaning or concept represented by the word {word}",
        "example": f"This is an example sentence using the word {word}",
        "prompt_image_guideline": f"A simple minimalist illustration representing the concept of {word} in educational cartoon style for vocabulary learning"
    }


@app.route('/api/csv/generate', methods=['POST'])
def api_generate_csv():
    """Generate CSV data from a list of words."""
    data = request.get_json() or {}
    words = data.get('words', [])
    include_examples = data.get('include_examples', True)
    include_prompts = data.get('include_prompts', True)
    vocabulary_type = data.get('vocabulary_type', 'GeneralEnglish')
    revision = data.get('revision', 1)
    target_revision = data.get('target_revision', 5)
    
    if not words:
        return jsonify({"success": False, "error": "No words provided"})
    
    csv_data = []
    for word in words:
        entry = generate_vocabulary_entry(word)
        
        if not include_examples:
            entry["example"] = ""
        if not include_prompts:
            entry["prompt_image_guideline"] = ""
        
        # Add new fields
        entry["vocabulary_type"] = vocabulary_type
        entry["revision"] = revision
        entry["target_revision"] = target_revision
        
        csv_data.append(entry)
    
    return jsonify({
        "success": True,
        "csv_data": csv_data,
        "count": len(csv_data)
    })


@app.route('/api/csv/load-to-db', methods=['POST'])
def api_load_csv_to_db():
    """Load generated CSV data to the vocabulary database."""
    from src.csv_reader import add_word
    
    data = request.get_json() or {}
    words = data.get('words', [])
    
    if not words:
        return jsonify({"success": False, "error": "No words provided"})
    
    count = 0
    for entry in words:
        try:
            add_word(
                word=entry.get('word', ''),
                definition=entry.get('definition', ''),
                example=entry.get('example', ''),
                prompt_image_guideline=entry.get('prompt_image_guideline', ''),
                vocabulary_type=entry.get('vocabulary_type', 'GeneralEnglish'),
                revision=entry.get('revision', 1),
                target_revision=entry.get('target_revision', 5)
            )
            count += 1
        except Exception as e:
            print(f"Failed to add word {entry.get('word')}: {e}")
    
    return jsonify({
        "success": True,
        "count": count,
        "message": f"Added {count} words to database"
    })


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("  VOCABULARY REELS GENERATOR")
    print("  Docker Container Starting...")
    print("=" * 60)
    print(f"  Web UI:    http://localhost:{config.API_PORT}")
    print(f"  API:       http://localhost:{config.API_PORT}/api/")
    print(f"  Health:    http://localhost:{config.API_PORT}/api/health")
    print("=" * 60)
    print(f"  ComfyUI:   {config.COMFYUI_URL}")
    print(f"  TTS:       {config.TTS_URL}")
    print("=" * 60)
    
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.DEBUG,
        threaded=True
    )
