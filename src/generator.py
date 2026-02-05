# Video Generator Service
# Orchestrates the complete video generation pipeline

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import sys
sys.path.append(str(Path(__file__).parent.parent))

import config
from src.csv_reader import update_word_status
from src.comfyui_client import generate_vocab_image, check_comfyui_status
from src.tts_client import generate_vocab_audio, check_tts_status
from src.video_composer import create_video_frame, create_video_with_audio, check_ffmpeg


class VideoGenerator:
    """Service to generate vocabulary videos."""
    
    def __init__(self):
        self.status = {
            "current_word": None,
            "current_step": None,
            "progress": 0,
            "error": None,
            "is_processing": False
        }
    
    def get_status(self) -> Dict:
        return self.status.copy()
    
    def check_services(self) -> Dict:
        """Check all required services."""
        comfyui = check_comfyui_status()
        tts = check_tts_status()
        ffmpeg = check_ffmpeg()
        
        return {
            "comfyui": comfyui,
            "tts": tts,
            "ffmpeg": {"installed": ffmpeg},
            "all_ok": comfyui["running"] and ffmpeg
        }
    
    def generate_video(self, word: str, definition: str, example: str = "",
                       custom_image_path: Optional[Path] = None,
                       word_index: Optional[int] = None) -> Dict:
        """
        Generate a complete vocabulary video.
        
        Args:
            word: The vocabulary word
            definition: Word definition
            example: Optional example sentence
            custom_image_path: Optional path to user-uploaded image
            word_index: Optional CSV index to update status
        
        Returns:
            Dict with video_path, success status, and any errors
        """
        self.status = {
            "current_word": word, 
            "current_step": "initializing", 
            "progress": 0, 
            "error": None,
            "is_processing": True
        }
        
        # Generate safe filename
        safe_name = "".join(c if c.isalnum() else "_" for c in word.lower())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Paths
        image_path = config.TEMP_DIR / f"{safe_name}_image.png"
        audio_path = config.TEMP_DIR / f"{safe_name}_audio.mp3"
        frame_path = config.TEMP_DIR / f"{safe_name}_frame.png"
        video_path = config.OUTPUT_DIR / f"{safe_name}_{timestamp}.mp4"
        
        try:
            # Step 1: Get/Generate Image
            self.status["current_step"] = "generating_image"
            self.status["progress"] = 10
            
            if custom_image_path and Path(custom_image_path).exists():
                # Use custom uploaded image
                image_path = Path(custom_image_path)
                self.status["progress"] = 40
            else:
                # Generate with ComfyUI
                generate_vocab_image(word, definition, image_path)
                self.status["progress"] = 40
            
            # Step 2: Generate Audio
            self.status["current_step"] = "generating_audio"
            generate_vocab_audio(word, definition, audio_path, example)
            self.status["progress"] = 70
            
            # Step 3: Create Video Frame
            self.status["current_step"] = "creating_frame"
            create_video_frame(word, definition, image_path, frame_path)
            self.status["progress"] = 85
            
            # Step 4: Compose Video with Audio
            self.status["current_step"] = "composing_video"
            create_video_with_audio(frame_path, audio_path, video_path)
            self.status["progress"] = 100
            
            # Cleanup temp files (but not custom uploaded images)
            if not custom_image_path:
                image_path.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)
            frame_path.unlink(missing_ok=True)
            
            # Update CSV if index provided
            if word_index is not None:
                update_word_status(word_index, "completed", str(video_path))
            
            self.status["current_step"] = "completed"
            self.status["is_processing"] = False
            
            return {
                "success": True,
                "video_path": str(video_path),
                "video_filename": video_path.name,
                "word": word
            }
            
        except Exception as e:
            self.status["error"] = str(e)
            self.status["current_step"] = "failed"
            self.status["is_processing"] = False
            
            if word_index is not None:
                update_word_status(word_index, f"failed: {str(e)[:100]}")
            
            return {
                "success": False,
                "error": str(e),
                "word": word
            }
    
    def generate_image_only(self, word: str, definition: str) -> Dict:
        """Generate only the image (for preview)."""
        safe_name = "".join(c if c.isalnum() else "_" for c in word.lower())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = config.OUTPUT_DIR / f"{safe_name}_{timestamp}_preview.png"
        
        try:
            generate_vocab_image(word, definition, image_path)
            return {
                "success": True, 
                "image_path": str(image_path), 
                "image_filename": image_path.name
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_audio_only(self, word: str, definition: str, example: str = "") -> Dict:
        """Generate only the audio (for preview)."""
        safe_name = "".join(c if c.isalnum() else "_" for c in word.lower())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = config.OUTPUT_DIR / f"{safe_name}_{timestamp}_preview.mp3"
        
        try:
            generate_vocab_audio(word, definition, audio_path, example)
            return {
                "success": True, 
                "audio_path": str(audio_path), 
                "audio_filename": audio_path.name
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
generator = VideoGenerator()
