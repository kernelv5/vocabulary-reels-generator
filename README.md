# Vocabulary Reels Generator


## 📌 Version Info

| Property | Value |
|----------|-------|
| **Version** | `4.0.0` |
| **Branch** | `version-4` |
| **Commit** | `c7dc050` |
| **Last Updated** | 2026-02-06 09:30:55 +0800 |
| **Description** | Added version info display on homepage |


## 🚀 Quick Start

### Prerequisites
Make sure these services are running on your **host machine**:
- **Chatterbox TTS Server** at `http://localhost:8004`

### Run with Docker

```bash
# Navigate to project folder
cd "C:\Users\admin\Documents\Claude-Document\vocabulary-reels-generator"

# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f
```

### Access the Application
- **Web UI**: http://localhost:5000

## 📁 Project Structure

```
vocabulary-reels-generator/
├── app.py                      # Main Flask app with Web UI + REST API
├── config.py                   # Configuration settings
├── layout_config.json          # Visual layout configuration (editable via UI)
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Container build instructions
├── requirements.txt            # Python dependencies
├── csv_database_doNotTouch.csv # Internal word database (auto-managed)
├── csv_input/                  # Sample CSV files for import
├── src/
│   ├── generator_v2.py         # Main video generation pipeline (uses layout_config.json)
│   ├── video_composer_v2.py    # FFmpeg video creation with layout support
│   ├── preview_generator.py    # Layout preview generation
│   ├── tts_client.py           # Text-to-speech client
│   ├── csv_reader.py           # CSV file handling
│   ├── layout_config.py        # Layout configuration loader
│   └── layout_editor_routes.py # Layout editor API endpoints
├── output/                     # Generated videos (Docker volume)
├── temp/                       # Temporary files

```

## 🎨 Key Features

### Layout Editor
- Visual drag-and-drop layout configuration
- Per-element margins (left/right) for word, definition, example, branding
- Real-time preview of layout changes
- All settings saved to `layout_config.json`

### Video Generation
- Text-to-speech via Chatterbox TTS
- FFmpeg video composition with audio sync

### Batch Processing
- Import vocabulary from CSV files
- Generate all videos with progress tracking
- Download individual or batch videos

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/status` | Check all services status |
| GET | `/api/words` | List all vocabulary words |
| POST | `/api/words` | Add new word |
| DELETE | `/api/words/{index}` | Delete word |
| DELETE | `/api/words/clear` | Clear all words |
| POST | `/api/generate/{index}` | Generate video by index |
| POST | `/api/upload/csv` | Import CSV file |
| GET | `/api/download/{file}` | Download file |
| GET | `/api/files` | List output files |
| DELETE | `/api/files/clear` | Clear all output files |
| GET | `/api/layout` | Get layout config |
| POST | `/api/layout` | Update layout config |
| GET | `/api/preview` | Generate layout preview |

## 🐳 Docker Commands

```bash
# Build and start
docker-compose up -d --build

# Stop
docker-compose down

# Rebuild without cache
docker-compose build --no-cache

# View logs
docker-compose logs -f

# Enter container
docker exec -it vocab-reels-generator bash
```

## 📊 CSV Import Format

```csv
word,definition,example
Serendipity,Finding something good by chance,It was serendipity that we met.
```

**Note:** Only `word` and `definition` are required. Avoid commas within fields.

## ⚙️ Configuration

### layout_config.json
Controls all visual aspects:
- Canvas size (1080x1920 for 9:16)
- Element positions (word, definition, example, branding)
- Font sizes and colors
- Video duration and quality

### Environment Variables (docker-compose.yml)
| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_URL` | `http://host.docker.internal:8004/v1/audio/speech` | TTS server |

## 🛠️ Troubleshooting

### Container can't connect to services
Services run on host machine. Docker uses `host.docker.internal` to reach them.

### Check service status
Visit http://localhost:5000 and check the status indicator for TTS.

### View container logs
```bash
docker-compose logs -f
```

## 🤖 AI Assistant Context
See `AI_CONTEXT.md` for comprehensive project information to help AI assistants understand this codebase.

## 📜 License
MIT License
