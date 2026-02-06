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
    
    def get_status(self) -> Dict:
        return self.status.copy()
    
    def check_services(self) -> Dict:
        """Check all required services."""
        tts = check_tts_status()
        ffmpeg = check_ffmpeg()
        
        return {
            "tts": tts,
            "ffmpeg": {"installed": ffmpeg},
            "all_ok": ffmpeg and tts.get("running", False)
        }
    
    def generate_video(self, 
                      word: str, 
                      definition: str, 
                      example: str = "",
                      word_index: Optional[int] = None,
                      vocabulary_type: str = "GeneralEnglish",
                      revision: int = 1,
                      target_revision: int = 5) -> Dict:
        """
        Generate a complete vocabulary video.
        
        Args:
            word: The vocabulary word
            definition: Word definition
            example: Optional example sentence
            word_index: Optional CSV index to update status
            vocabulary_type: Type of vocabulary (e.g., GeneralEnglish, BusinessEnglish)
            revision: Current revision count
            target_revision: Target revision count
        
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
        
        # Generate filename: VocabularyType_Word_Revision_TargetRevision.mp4
        safe_word = "".join(c if c.isalnum() else "_" for c in word)
        safe_type = "".join(c if c.isalnum() else "" for c in vocabulary_type)
        video_filename = f"{safe_type}_{safe_word}_{revision}_{target_revision}.mp4"
        
        # Paths
        safe_name = safe_word.lower()
        audio_path = config.TEMP_DIR / f"{safe_name}_audio.mp3"
        frame_path = config.TEMP_DIR / f"{safe_name}_frame.png"
        video_path = config.OUTPUT_DIR / video_filename
        
        try:
            # Step 1: Generate Audio
            self.status["current_step"] = "generating_audio"
            generate_vocab_audio(word, definition, audio_path, example)
            self.status["progress"] = 50
            
            # Step 2: Create Video Frame
            self.status["current_step"] = "creating_frame"
            create_video_frame(word, definition, example, frame_path)
            self.status["progress"] = 80
            
            # Step 3: Compose Video with Audio
            self.status["current_step"] = "composing_video"
            create_video_with_audio(frame_path, audio_path, video_path)
            self.status["progress"] = 100
            
            # Cleanup temp files
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
