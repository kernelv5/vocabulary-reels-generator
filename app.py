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
    POST /api/generate/audio      - Generate audio only (preview)
    POST /api/generate/batch      - Generate videos for all pending words
    POST /api/upload/csv          - Upload CSV file with vocabulary
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
ALLOWED_EXTENSIONS = {'csv'}
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
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
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
            formData.append('vocabulary_type', document.getElementById('vocabulary-type').value || 'GeneralEnglish');
            formData.append('revision', document.getElementById('revision').value || '1');
            formData.append('target_revision', document.getElementById('target-revision').value || '5');
            
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
                
                <!-- Example -->
                <div class="card">
                    <div class="section-title"><i class="fas fa-quote-left text-green-500"></i> Example</div>
                    <div class="element-card">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="input-group">
                                <label>Y:</label>
                                <input type="number" id="ex-y" min="0" max="1500" value="800" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>H:</label>
                                <input type="number" id="ex-h" min="50" max="800" value="600" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-4 mt-3">
                            <div class="input-group">
                                <label>Left:</label>
                                <input type="number" id="ex-left" min="0" max="500" value="100" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Right:</label>
                                <input type="number" id="ex-right" min="0" max="500" value="100" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                        </div>
                        <div class="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-gray-200">
                            <div class="input-group">
                                <label>Font:</label>
                                <input type="number" id="ex-font-size" min="16" max="72" value="38" onchange="update()">
                                <span class="text-gray-400 text-sm">px</span>
                            </div>
                            <div class="input-group">
                                <label>Wt:</label>
                                <select id="ex-font-weight" class="p-2 border rounded-lg text-sm" onchange="update()">
                                    <option value="normal" selected>Normal</option>
                                    <option value="bold">Bold</option>
                                </select>
                            </div>
                            <div class="input-group">
                                <label>Line:</label>
                                <input type="number" id="ex-line-spacing" min="1.0" max="3.0" step="0.1" value="1.4" onchange="update()">
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
                        <div>
                            <label class="block text-xs font-semibold text-gray-500 mb-1">Preview Example:</label>
                            <textarea id="preview-example" rows="2" 
                                      class="w-full p-2 text-sm border rounded-lg" onchange="update()" oninput="update()" 
                                      placeholder="Enter example...">The team decided to disband after the project ended</textarea>
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
                example: { y_start: 800, y_end: 1400, height: 600, left_margin: 100, right_margin: 100, font_size: 38, font_weight: 'normal', line_spacing: 1.4 },
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
            
            // Example
            document.getElementById('ex-y').value = config.elements.example.y_start || 800;
            document.getElementById('ex-h').value = config.elements.example.height || 600;
            document.getElementById('ex-left').value = config.elements.example.left_margin || 100;
            document.getElementById('ex-right').value = config.elements.example.right_margin || 100;
            document.getElementById('ex-font-size').value = config.elements.example.font_size || 38;
            document.getElementById('ex-font-weight').value = config.elements.example.font_weight || 'normal';
            document.getElementById('ex-line-spacing').value = config.elements.example.line_spacing || 1.4;
            
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
                example: {
                    y: parseInt(document.getElementById('ex-y').value),
                    h: parseInt(document.getElementById('ex-h').value),
                    left: parseInt(document.getElementById('ex-left').value),
                    right: parseInt(document.getElementById('ex-right').value),
                    fontSize: parseInt(document.getElementById('ex-font-size').value),
                    fontWeight: document.getElementById('ex-font-weight').value,
                    lineSpacing: parseFloat(document.getElementById('ex-line-spacing').value)
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
                previewDefinition: document.getElementById('preview-definition').value || 'To break up or stop working together as a group',
                previewExample: document.getElementById('preview-example').value || 'The team decided to disband after the project ended'
            };
        }
        
        function update() {
            const v = getUIValues();
            const exampleHtml = highlightExampleWord(v.previewExample, v.previewWord, v.example.fontSize);
            
            // Update safe width display
            const safeWidth = v.safe.right - v.safe.left;
            document.getElementById('safe-width').textContent = safeWidth;
            
            // Scale values for preview (1/4 scale)
            const s = (val) => val / SCALE;
            
            // Calculate individual element widths based on their margins
            const wordWidth = 1080 - v.word.left - v.word.right;
            const defWidth = 1080 - v.def.left - v.def.right;
            const exampleWidth = 1080 - v.example.left - v.example.right;
            const brandWidth = 1080 - v.brand.left - v.brand.right;
            
            // Calculate center X for each element
            const wordCenterX = v.word.left + wordWidth / 2;
            const defCenterX = v.def.left + defWidth / 2;
            const exampleCenterX = v.example.left + exampleWidth / 2;
            const brandCenterX = v.brand.left + brandWidth / 2;
            
            // Build preview HTML
            const previewHTML = `
                <!-- Safe Area (Reference) -->
                <div class="safe-area" style="left:${s(v.safe.left)}px;right:${s(1080-v.safe.right)}px;top:0;bottom:0;"></div>
                
                <!-- Guide Lines -->
                <div class="guide-line" style="top:${s(v.word.y)}px;" data-label="${v.word.y}"></div>
                <div class="guide-line" style="top:${s(v.word.y + v.word.h)}px;"></div>
                <div class="guide-line" style="top:${s(v.def.y + v.def.h)}px;background:rgba(59,130,246,0.5);"></div>
                <div class="guide-line" style="top:${s(v.example.y)}px;background:rgba(16,185,129,0.5);"></div>
                <div class="guide-line" style="top:${s(v.example.y + v.example.h)}px;background:rgba(16,185,129,0.5);"></div>
                <div class="guide-line" style="top:${s(v.brand.y)}px;background:rgba(249,115,22,0.5);"></div>
                
                <!-- Word -->
                <div class="element-preview" style="top:${s(v.word.y)}px;left:${s(v.word.left)}px;width:${s(wordWidth)}px;height:${s(v.word.h)}px;font-size:${s(v.word.fontSize)}px;font-weight:${v.word.fontWeight};line-height:${s(v.word.h)}px;color:#232323;">
                    ${v.previewWord}
                </div>
                
                <!-- Definition -->
                <div class="element-preview" style="top:${s(v.def.y)}px;left:${s(v.def.left)}px;width:${s(defWidth)}px;height:${s(v.def.h)}px;font-size:${s(v.def.fontSize)}px;font-weight:${v.def.fontWeight};line-height:${v.def.lineSpacing};color:#3c3c3c;overflow:hidden;">
                    ${v.previewDefinition}
                </div>
                
                <!-- Example -->
                <div class="element-preview" style="top:${s(v.example.y)}px;left:${s(v.example.left)}px;width:${s(exampleWidth)}px;height:${s(v.example.h)}px;font-size:${s(v.example.fontSize)}px;font-weight:${v.example.fontWeight};line-height:${v.example.lineSpacing};color:#3c3c3c;overflow:hidden;">
                    ${exampleHtml}
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
            
            // Example
            config.elements.example.y_start = v.example.y;
            config.elements.example.y_end = v.example.y + v.example.h;
            config.elements.example.height = v.example.h;
            config.elements.example.left_margin = v.example.left;
            config.elements.example.right_margin = v.example.right;
            config.elements.example.font_size = v.example.fontSize;
            config.elements.example.font_weight = v.example.fontWeight;
            config.elements.example.line_spacing = v.example.lineSpacing;
            
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

        function escapeRegExp(text) {
            return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }

        function highlightExampleWord(text, word, baseFontSize) {
            if (!text || !word) return text || '';
            const size = baseFontSize + 2;
            const regex = new RegExp(`\\b(${escapeRegExp(word)})\\b`, 'gi');
            return text.replace(regex, (match) => `<span style="font-weight:700;font-size:${size}px;">${match}</span>`);
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
            document.getElementById('ex-y').value = 800;
            document.getElementById('ex-h').value = 600;
            document.getElementById('ex-left').value = 100;
            document.getElementById('ex-right').value = 100;
            document.getElementById('ex-font-size').value = 38;
            document.getElementById('ex-font-weight').value = 'normal';
            document.getElementById('ex-line-spacing').value = 1.4;
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
                    body: JSON.stringify({ word: v.previewWord, definition: v.previewDefinition, example: v.previewExample, show_guides: true })
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
    
    if not word or not definition:
        return jsonify({"error": "word and definition are required"}), 400
    
    index = add_word(word, definition, example)
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
        vocabulary_type = request.form.get('vocabulary_type', 'GeneralEnglish')
        revision = int(request.form.get('revision', 1))
        target_revision = int(request.form.get('target_revision', 5))
    else:
        data = request.get_json() or {}
        word = data.get('word')
        definition = data.get('definition')
        example = data.get('example', '')
        vocabulary_type = data.get('vocabulary_type', 'GeneralEnglish')
        revision = int(data.get('revision', 1))
        target_revision = int(data.get('target_revision', 5))
    
    if not word or not definition:
        return jsonify({"error": "word and definition are required"}), 400
    
    result = generator.generate_video(
        word=word, 
        definition=definition, 
        example=example,
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
        word_index=index,
        vocabulary_type=word_data.get('vocabulary_type', 'GeneralEnglish'),
        revision=word_data.get('revision', 1),
        target_revision=word_data.get('target_revision', 5)
    )
    return jsonify(result)


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
    example = data.get('example', 'The team decided to disband after the project ended')
    show_guides = data.get('show_guides', True)
    
    try:
        preview_path = create_preview(word, definition, example, show_guides=show_guides)
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
    example = data.get('example', 'The team decided to disband after the project ended')
    show_guides = data.get('show_guides', False)
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"preview_{timestamp}.png"
        
        preview_path = create_preview(word, definition, example, output_path, show_guides)
        
        return send_file(
            preview_path,
            as_attachment=True,
            download_name=f"layout_preview_{timestamp}.png"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    print(f"  TTS:       {config.TTS_URL}")
    print("=" * 60)
    
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.DEBUG,
        threaded=True
    )
