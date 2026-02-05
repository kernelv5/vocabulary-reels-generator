# Vocabulary Reels Generator

A Dockerized solution for generating YouTube Shorts-style vocabulary videos with AI-powered images and voice.

## 🚀 Quick Start

### Prerequisites
Make sure these are running on your **host machine**:
- **ComfyUI** at `http://127.0.0.1:8188` (with DreamShaperXL_Lightning model)
- **TTS Server** at `http://localhost:8004`

### Run with Docker

```bash
# Navigate to project folder
cd "C:\Users\admin\Documents\Claude-Document\vocabulary-reels-generator"

# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

### Access the Application

- **Web UI**: http://localhost:5000
- **API**: http://localhost:5000/api/

## 📁 Project Structure

```
vocabulary-reels-generator/
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── config.py               # Application configuration
├── app.py                  # Main Flask application (UI + API)
├── vocabulary.csv          # Sample vocabulary data
├── src/
│   ├── __init__.py
│   ├── csv_reader.py       # CSV file handling
│   ├── comfyui_client.py   # ComfyUI integration
│   ├── tts_client.py       # TTS server integration
│   ├── video_composer.py   # FFmpeg video creation
│   └── generator.py        # Main generation pipeline
├── output/                 # Generated videos (mounted volume)
└── uploads/                # Uploaded images (mounted volume)
```

## 🐳 Docker Commands

```bash
# Build the image
docker-compose build

# Start the container
docker-compose up -d

# Stop the container
docker-compose down

# View logs
docker-compose logs -f

# Rebuild and restart
docker-compose up -d --build

# Enter container shell
docker exec -it vocab-reels-generator bash
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/status` | Check all services |
| GET | `/api/words` | List all words |
| POST | `/api/words` | Add new word |
| DELETE | `/api/words/{index}` | Delete word |
| POST | `/api/generate` | Generate video |
| POST | `/api/generate/{index}` | Generate by index |
| POST | `/api/generate/batch` | Generate all pending |
| POST | `/api/generate/image` | Preview image only |
| POST | `/api/generate/audio` | Preview audio only |
| POST | `/api/upload/csv` | Upload CSV file |
| GET | `/api/download/{file}` | Download file |
| GET | `/api/files` | List output files |

### Example: Generate Video

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"word": "Serendipity", "definition": "Finding something good by chance"}'
```

### Example: Upload CSV

```bash
curl -X POST http://localhost:5000/api/upload/csv \
  -F "csv_file=@vocabulary.csv"
```

## 🔗 n8n Integration

### Webhook → Generate Video

```
[Webhook Trigger]
       ↓
[HTTP Request]
  POST http://localhost:5000/api/generate
  Body: {"word": "{{$json.word}}", "definition": "{{$json.definition}}"}
       ↓
[IF success]
       ↓
[HTTP Request]
  GET http://localhost:5000/api/download/{{$json.video_filename}}
```

### Google Sheets → Batch Generate

```
[Schedule Trigger]
       ↓
[Google Sheets: Get Rows]
       ↓
[HTTP Request]
  POST http://localhost:5000/api/upload/csv
       ↓
[HTTP Request]
  POST http://localhost:5000/api/generate/batch
       ↓
[Slack: Notify completion]
```

## ⚙️ Environment Variables

Configure in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMFYUI_URL` | `http://host.docker.internal:8188` | ComfyUI server URL |
| `TTS_URL` | `http://host.docker.internal:8004/v1/audio/speech` | TTS server URL |
| `COMFYUI_MODEL` | `DreamShaperXL_Lightning.safetensors` | SD model name |
| `TTS_VOICE` | `alloy` | TTS voice |
| `TTS_SPEED` | `1.0` | Speech speed |
| `CHANNEL_NAME` | `@YourChannel` | Branding text |
| `API_PORT` | `5000` | Server port |

## 📊 CSV Format

```csv
word,definition,example,status,video_path
Serendipity,Finding something good by chance,It was serendipity.,pending,
```

| Column | Required | Description |
|--------|----------|-------------|
| word | ✅ | Vocabulary word |
| definition | ✅ | Word meaning |
| example | ❌ | Example sentence |
| status | Auto | pending/completed/failed |
| video_path | Auto | Generated video path |

## 🛠️ Troubleshooting

### Container can't connect to ComfyUI/TTS

The container uses `host.docker.internal` to reach services on your host machine.

**Windows/Mac**: Works automatically.

**Linux**: Add to docker-compose.yml:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

### ComfyUI model not found

Ensure the model file exists in:
```
C:\Users\admin\Documents\ComfyUI_windows_portable\ComfyUI\models\checkpoints\DreamShaperXL_Lightning.safetensors
```

### Video generation fails

1. Check ComfyUI is running: http://127.0.0.1:8188
2. Check TTS is running: http://localhost:8004
3. View container logs: `docker-compose logs -f`

## 📜 License

MIT License - Feel free to use and modify!
