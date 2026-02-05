# TTS Client Module
# Generates voice audio using local Chatterbox TTS server
# Uses the /tts endpoint with clone voice mode

import requests
import subprocess
import json
from pathlib import Path
from typing import Optional
import sys
sys.path.append(str(Path(__file__).parent.parent))
import config


class TTSClient:
    """Client for local Chatterbox TTS server using /tts endpoint."""
    
    def __init__(self, server_url: str = None):
        base_url = (server_url or config.TTS_URL).replace('/v1/audio/speech', '').replace('/tts', '')
        self.tts_url = f"{base_url}/tts"
        self.base_url = base_url
        self.reference_voice = config.TTS_VOICE
    
    def is_server_running(self) -> bool:
        """Check if TTS server is running."""
        try:
            response = requests.get(self.base_url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"TTS health check failed: {e}")
            return False
    
    def get_reference_files(self) -> list:
        """Get available reference audio files."""
        try:
            response = requests.get(f"{self.base_url}/get_reference_files", timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []
    
    def generate_speech(self, text: str, output_path: Path,
                       exaggeration: float = 0.5, cfg_weight: float = 0.5,
                       temperature: float = 0.8) -> Path:
        """
        Generate speech audio using clone voice mode with reference file.
        
        Args:
            text: Text to synthesize
            output_path: Where to save the audio
            exaggeration: Voice exaggeration (0.25-2.0)
            cfg_weight: CFG weight (0.0-1.0)
            temperature: Generation temperature
        """
        
        # Get reference voice file
        reference_file = self.reference_voice
        if not reference_file:
            refs = self.get_reference_files()
            reference_file = refs[0] if refs else "Gianna.wav"
        
        # Ensure .wav extension
        if not reference_file.endswith('.wav'):
            reference_file = f"{reference_file}.wav"
        
        # Chatterbox /tts endpoint payload with clone mode
        payload = {
            "text": text,
            "voice_mode": "clone",
            "reference_audio_filename": reference_file,
            "output_format": "wav",
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
            "temperature": temperature,
            "split_text": False
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        print(f"  TTS Request to: {self.tts_url}")
        print(f"  Voice mode: clone")
        print(f"  Reference file: {reference_file}")
        print(f"  Text: {text[:50]}...")
        
        response = requests.post(
            self.tts_url, 
            json=payload, 
            headers=headers,
            timeout=180
        )
        
        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save WAV first
            wav_path = output_path.with_suffix('.wav')
            with open(wav_path, "wb") as f:
                f.write(response.content)
            
            # Convert to MP3 if needed
            if output_path.suffix.lower() == '.mp3':
                convert_cmd = [
                    "ffmpeg", "-y", "-i", str(wav_path),
                    "-acodec", "libmp3lame", "-b:a", "192k",
                    str(output_path)
                ]
                result = subprocess.run(convert_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    wav_path.unlink(missing_ok=True)
                else:
                    print(f"  MP3 conversion failed: {result.stderr}")
                    # Use WAV if conversion fails
                    if wav_path.exists():
                        output_path = wav_path
            else:
                if wav_path != output_path:
                    wav_path.rename(output_path)
            
            print(f"  TTS Success: Saved to {output_path}")
            return output_path
        else:
            error_msg = f"TTS failed: {response.status_code} - {response.text}"
            print(f"  TTS Error: {error_msg}")
            raise Exception(error_msg)


def generate_vocab_audio(word: str, definition: str, output_path: Path, example: str = "") -> Path:
    """Generate audio narration for a vocabulary word."""
    client = TTSClient()
    
    script = config.VOICE_SCRIPT_TEMPLATE.format(word=word, definition=definition)
    if example and example.strip():
        script += f" For example: {example}"
    
    return client.generate_speech(script, output_path)


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration using ffprobe."""
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 5.0


def check_tts_status() -> dict:
    """Check TTS server status."""
    client = TTSClient()
    running = client.is_server_running()
    refs = client.get_reference_files() if running else []
    
    return {
        "running": running,
        "url": client.tts_url,
        "voice_mode": "clone",
        "reference_voice": client.reference_voice or "Gianna.wav",
        "available_references": refs,
        "server_type": "Chatterbox TTS"
    }
