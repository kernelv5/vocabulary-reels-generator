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
                <div class="text-right text-sm text-purple-200">
                    <div>Docker Container</div>
                    <div id="container-status" class="font-mono">Running</div>
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
                                <i class="fas fa-image mr-1"></i> Custom Image (optional)
                            </label>
                            <input type="file" id="custom-image" name="custom_image" accept="image/*"
                                   class="w-full px-4 py-3 border-2 border-dashed border-gray-300 rounded-xl hover:border-purple-400 transition cursor-pointer">
                            <p class="text-xs text-gray-500 mt-2">Upload your own image instead of AI-generated (PNG, JPG)</p>
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
                    <video id="result-video" controls class="w-full rounded-xl mb-4 shadow-lg"></video>
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
            
            // Definition
            document.getElementById('def-y').value = config.elements.definition.y_start || 230;
            document.getElementById('def-h').value = config.elements.definition.height || 75;
            document.getElementById('def-left').value = config.elements.definition.left_margin || 270;
            document.getElementById('def-right').value = config.elements.definition.right_margin || 270;
            
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
                    right: parseInt(document.getElementById('word-right').value)
                },
                def: {
                    y: parseInt(document.getElementById('def-y').value),
                    h: parseInt(document.getElementById('def-h').value),
                    left: parseInt(document.getElementById('def-left').value),
                    right: parseInt(document.getElementById('def-right').value)
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
                channelName: document.getElementById('channel-name').value
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
                <div class="element-preview" style="top:${s(v.word.y)}px;left:${s(v.word.left)}px;width:${s(wordWidth)}px;height:${s(v.word.h)}px;font-size:${s(72)}px;font-weight:bold;line-height:${s(v.word.h)}px;color:#232323;">
                    Disband
                </div>
                
                <!-- Definition -->
                <div class="element-preview" style="top:${s(v.def.y)}px;left:${s(v.def.left)}px;width:${s(defWidth)}px;height:${s(v.def.h)}px;font-size:${s(32)}px;line-height:1.3;color:#3c3c3c;overflow:hidden;">
                    To break up or stop working together as a group...
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
            
            // Definition
            config.elements.definition.y_start = v.def.y;
            config.elements.definition.y_end = v.def.y + v.def.h;
            config.elements.definition.height = v.def.h;
            config.elements.definition.left_margin = v.def.left;
            config.elements.definition.right_margin = v.def.right;
            
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
            document.getElementById('def-y').value = 230;
            document.getElementById('def-h').value = 75;
            document.getElementById('def-left').value = 270;
            document.getElementById('def-right').value = 270;
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
            try {
                const res = await fetch('/api/preview/layout', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ word: 'Disband', definition: 'To break up or stop working together as a group', show_guides: true })
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
        custom_image_path = data.get('custom_image_path')
    
    if not word or not definition:
        return jsonify({"error": "word and definition are required"}), 400
    
    result = generator.generate_video(word, definition, example, custom_image_path)
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
        word_index=index
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
    """Generate image with advanced options (seed, steps, cfg, etc.)."""
    from src.image_generator_advanced import generate_vocab_image_advanced
    
    data = request.get_json() or {}
    
    word = data.get('word')
    definition = data.get('definition')
    
    if not word or not definition:
        return jsonify({"error": "word and definition required"}), 400
    
    # Optional parameters
    kwargs = {}
    if 'custom_prompt' in data:
        kwargs['custom_prompt'] = data['custom_prompt']
    if 'custom_negative' in data:
        kwargs['custom_negative'] = data['custom_negative']
    if 'seed' in data:
        kwargs['seed'] = int(data['seed'])
    if 'steps' in data:
        kwargs['steps'] = int(data['steps'])
    if 'cfg_scale' in data:
        kwargs['cfg_scale'] = float(data['cfg_scale'])
    if 'width' in data:
        kwargs['width'] = int(data['width'])
    if 'height' in data:
        kwargs['height'] = int(data['height'])
    if 'sampler' in data:
        kwargs['sampler'] = data['sampler']
    if 'remove_background' in data:
        kwargs['remove_background'] = bool(data['remove_background'])
    
    # Generate filename
    safe_name = "".join(c if c.isalnum() else "_" for c in word.lower())
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = config.OUTPUT_DIR / f"{safe_name}_image_{timestamp}.png"
    
    result = generate_vocab_image_advanced(word, definition, output_path, **kwargs)
    
    if result.get('success'):
        result['image_url'] = f"/output/{output_path.name}"
    
    return jsonify(result)


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
