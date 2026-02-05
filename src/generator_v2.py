"""
Video Generator Service V2 - Using layout_config.json and advanced features
Orchestrates the complete video generation pipeline with configuration support
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import sys

sys.path.append(str(Path(__file__).parent.parent))

import config
from src.csv_reader import update_word_status
from src.tts_client import generate_vocab_audio, check_tts_status
from src.video_composer_v2 import create_video_frame, create_video_with_audio, check_ffmpeg
from src.image_generator_advanced import AdvancedImageGenerator
from src.layout_config import get_layout_config


class VideoGeneratorV2:
    """Service to generate vocabulary videos with advanced configuration support."""
    
    def __init__(self):
        self.status = {
            "current_word": None,
            "current_step": None,
            "progress": 0,
            "error": None,
            "is_processing": False
        }
        self.image_generator = AdvancedImageGenerator()
    
    def get_status(self) -> Dict:
        return self.status.copy()
    
    def check_services(self) -> Dict:
        """Check all required services."""
        comfyui_running = self.image_generator.is_server_running()
        tts = check_tts_status()
        ffmpeg = check_ffmpeg()
        
        return {
            "comfyui": {
                "running": comfyui_running,
                "url": self.image_generator.comfyui_url
            },
            "tts": tts,
            "ffmpeg": {"installed": ffmpeg},
            "all_ok": comfyui_running and ffmpeg
        }
    
    def generate_video(self, 
                      word: str, 
                      definition: str, 
                      example: str = "",
                      custom_image_path: Optional[Path] = None,
                      word_index: Optional[int] = None,
                      image_gen_params: Optional[Dict] = None) -> Dict:
        """
        Generate a complete vocabulary video.
        
        Args:
            word: The vocabulary word
            definition: Word definition
            example: Optional example sentence
            custom_image_path: Optional path to user-uploaded image
            word_index: Optional CSV index to update status
            image_gen_params: Optional dict with: seed, steps, cfg_scale, custom_prompt, etc.
        
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
                # Generate with advanced options
                image_params = image_gen_params or {}
                result = self.image_generator.generate_image(
                    word=word,
                    definition=definition,
                    output_path=image_path,
                    **image_params
                )
                
                if not result.get('success'):
                    raise Exception(f"Image generation failed: {result.get('error')}")
                
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
    
    def generate_image_only(self, word: str, definition: str, **kwargs) -> Dict:
        """
        Generate only the image (for preview).
        
        Args:
            word: Vocabulary word
            definition: Definition
            **kwargs: Additional image generation parameters
        
        Returns:
            Result dict with image_path and metadata
        """
        safe_name = "".join(c if c.isalnum() else "_" for c in word.lower())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = config.OUTPUT_DIR / f"{safe_name}_{timestamp}_preview.png"
        
        try:
            result = self.image_generator.generate_image(
                word=word,
                definition=definition,
                output_path=image_path,
                **kwargs
            )
            
            if result.get('success'):
                result['image_filename'] = image_path.name
            
            return result
            
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


# Global instance for easy access
_generator_v2 = None

def get_video_generator() -> VideoGeneratorV2:
    """Get global VideoGeneratorV2 instance."""
    global _generator_v2
    if _generator_v2 is None:
        _generator_v2 = VideoGeneratorV2()
    return _generator_v2
