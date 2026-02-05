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
from src.generator import VideoGenerator

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for n8n integration

# File upload settings
ALLOWED_EXTENSIONS = {'csv', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Generator instance
generator = VideoGenerator()


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
                        <button onclick="generateBatch()"
                                class="bg-indigo-600 text-white py-2 px-4 rounded-lg hover:bg-indigo-700 transition text-sm font-medium shadow">
                            <i class="fas fa-play mr-1"></i>
                            Generate All
                        </button>
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
                        <button onclick="loadOutputFiles()" class="text-gray-500 hover:text-gray-700">
                            <i class="fas fa-sync-alt"></i>
                        </button>
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

        // Generate batch
        async function generateBatch() {
            if (!confirm('Generate videos for all pending words? This may take a while.')) return;
            
            try {
                const res = await fetch('/api/generate/batch', {method: 'POST'});
                const data = await res.json();
                alert(`Batch complete!\\n✓ Success: ${data.success_count}\\n✗ Failed: ${data.fail_count}`);
                loadWords();
                loadOutputFiles();
            } catch (e) {
                alert('Batch generation failed: ' + e.message);
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
    <title>Layout Editor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card { background: white; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); padding: 24px; }
        .tab-btn { padding: 12px 24px; border-radius: 8px; font-weight: 600; transition: all 0.3s; }
        .tab-btn.active { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .preview-box { width: 360px; height: 640px; background: white; margin: 0 auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3); border-radius: 24px; overflow: hidden; border: 8px solid #333; }
        .guide-line { position: absolute; width: 100%; height: 2px; background: rgba(102, 126, 234, 0.5); z-index: 10; }
        .toast { position: fixed; bottom: 30px; right: 30px; background: #10b981; color: white; padding: 16px 24px; border-radius: 12px; z-index: 1000; display: none; }
    </style>
</head>
<body class="bg-gray-50">
    <header class="gradient-bg text-white py-6">
        <div class="container mx-auto px-6">
            <div class="flex items-center gap-4">
                <a href="/" class="hover:text-purple-200"><i class="fas fa-arrow-left text-xl"></i></a>
                <h1 class="text-3xl font-bold">Layout Editor</h1>
            </div>
        </div>
    </header>
    <main class="container mx-auto px-6 py-8">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div class="lg:col-span-2">
                <div class="card">
                    <h2 class="text-2xl font-bold mb-6">Controls</h2>
                    <div class="space-y-6">
                        <div>
                            <label class="block mb-2">Word Y: <span id="word-y-val">175</span>px</label>
                            <input type="range" id="word-y" min="50" max="400" value="175" class="w-full" oninput="update()">
                        </div>
                        <div>
                            <label class="block mb-2">Definition Y: <span id="def-y-val">230</span>px</label>
                            <input type="range" id="def-y" min="100" max="500" value="230" class="w-full" oninput="update()">
                        </div>
                        <button onclick="save()" class="w-full bg-green-600 text-white py-3 rounded-lg font-semibold">
                            <i class="fas fa-check mr-2"></i>Save & Apply
                        </button>
                    </div>
                </div>
            </div>
            <div class="lg:col-span-1">
                <div class="card">
                    <h2 class="text-xl font-bold mb-4">Preview</h2>
                    <div id="preview" class="preview-box"></div>
                </div>
            </div>
        </div>
    </main>
    <div id="toast" class="toast"><i class="fas fa-check-circle mr-2"></i><span id="toast-msg"></span></div>
    <script>
        let config = null;
        async function load() {
            const res = await fetch('/api/layout/config');
            config = await res.json();
            document.getElementById('word-y').value = config.elements.word_title.y_start;
            document.getElementById('def-y').value = config.elements.definition.y_start;
            update();
        }
        function update() {
            document.getElementById('word-y-val').textContent = document.getElementById('word-y').value;
            document.getElementById('def-y-val').textContent = document.getElementById('def-y').value;
            const wordY = parseInt(document.getElementById('word-y').value) / 3;
            const defY = parseInt(document.getElementById('def-y').value) / 3;
            document.getElementById('preview').innerHTML = `<div style="position:relative;width:360px;height:640px;background:white;"><div style="position:absolute;top:${wordY}px;width:100%;text-align:center;font-size:24px;font-weight:bold;">Word</div><div style="position:absolute;top:${defY}px;width:100%;text-align:center;font-size:12px;">Definition goes here</div></div>`;
        }
        async function save() {
            config.elements.word_title.y_start = parseInt(document.getElementById('word-y').value);
            config.elements.definition.y_start = parseInt(document.getElementById('def-y').value);
            const res = await fetch('/api/layout/config', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(config)});
            const result = await res.json();
            if(result.success) {
                document.getElementById('toast-msg').textContent = 'Saved!';
                document.getElementById('toast').style.display = 'block';
                setTimeout(() => document.getElementById('toast').style.display = 'none', 3000);
            }
        }
        window.addEventListener('DOMContentLoaded', load);
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
    clear_all_words()
    return jsonify({"success": True})


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
    
    return jsonify({
        "success_count": success_count,
        "fail_count": fail_count,
        "total": len(pending),
        "results": results
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
