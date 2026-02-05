# JSON2Video Client Module
# Creates vocabulary videos using JSON2Video API for consistent design

import requests
import time
import json
from pathlib import Path
from typing import Optional, Dict
import sys
sys.path.append(str(Path(__file__).parent.parent))
import config


class JSON2VideoClient:
    """
    Client for JSON2Video API to create vocabulary reels with consistent design.
    
    API Documentation: https://json2video.com/docs/
    """
    
    BASE_URL = "https://api.json2video.com/v2"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.JSON2VIDEO_API_KEY
        self.template_id = config.JSON2VIDEO_TEMPLATE_ID  # Optional: use saved template
        
    def _headers(self) -> Dict:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def create_vocabulary_reel(
        self,
        word: str,
        definition: str,
        image_url: str,
        channel_name: str = "@WhiteEnglishVocabulary",
        voice_text: str = None
    ) -> Dict:
        """
        Create a vocabulary reel video using JSON2Video API.
        
        Layout specifications (matching your Canva design):
        - Canvas: 1080x1920 (9:16)
        - Safe area: 540px wide, centered (270px - 810px)
        - Word Title: Y=175-230 (55px height)
        - Definition: Y=230-305 (75px height)
        - Image: Y=305-530 (225px height, max 750px width)
        - Branding: Y=540-570 (30px height)
        
        Args:
            word: The vocabulary word
            definition: Word definition
            image_url: URL to the illustration image (should have transparent/white bg)
            channel_name: Your channel handle
            voice_text: Optional custom voice text (defaults to word + definition)
            
        Returns:
            Dict with project_id, status, and video_url when complete
        """
        
        if voice_text is None:
            voice_text = f"{word}. {definition}"
        
        # Build the movie JSON
        movie_json = {
            "comment": f"Vocabulary Reel: {word}",
            "resolution": "custom",
            "width": 1080,
            "height": 1920,
            "quality": "high",
            "fps": 30,
            
            "scenes": [
                {
                    "comment": "Main Vocabulary Scene",
                    "duration": 10,
                    "background-color": "#FFFFFF",
                    
                    "elements": [
                        # Word Title - Bold, at Y=175
                        {
                            "type": "text",
                            "text": word.capitalize(),
                            "position": "custom",
                            "x": 270,
                            "y": 175,
                            "width": 540,
                            "height": 55,
                            "duration": 10,
                            "start": 0,
                            "settings": {
                                "font-family": "Poppins",
                                "font-size": "72px",
                                "font-weight": "700",
                                "color": "#232323",
                                "text-align": "center",
                                "vertical-position": "middle",
                                "horizontal-position": "center"
                            }
                        },
                        
                        # Definition Text - at Y=230
                        {
                            "type": "text",
                            "text": definition,
                            "position": "custom",
                            "x": 270,
                            "y": 230,
                            "width": 540,
                            "height": 75,
                            "duration": 10,
                            "start": 0,
                            "settings": {
                                "font-family": "Poppins",
                                "font-size": "36px",
                                "font-weight": "400",
                                "color": "#3C3C3C",
                                "text-align": "center",
                                "vertical-position": "top",
                                "horizontal-position": "center",
                                "line-height": "1.4"
                            }
                        },
                        
                        # Illustration Image - at Y=305, centered
                        {
                            "type": "image",
                            "src": image_url,
                            "position": "custom",
                            "x": 165,
                            "y": 305,
                            "width": 750,
                            "height": 225,
                            "duration": 10,
                            "start": 0
                        },
                        
                        # Channel Branding - at Y=540
                        {
                            "type": "text",
                            "text": channel_name,
                            "position": "custom",
                            "x": 270,
                            "y": 540,
                            "width": 540,
                            "height": 30,
                            "duration": 10,
                            "start": 0,
                            "settings": {
                                "font-family": "Poppins",
                                "font-size": "28px",
                                "font-weight": "500",
                                "color": "#3C3C3C",
                                "text-align": "center",
                                "vertical-position": "middle",
                                "horizontal-position": "center"
                            }
                        },
                        
                        # AI Voice Narration
                        {
                            "type": "voice",
                            "text": voice_text,
                            "voice": "en-US-AriaNeural",
                            "speed": 0.9,
                            "start": 0.5
                        }
                    ]
                }
            ]
        }
        
        return self._render_movie(movie_json)
    
    def create_vocabulary_reel_with_template(
        self,
        template_id: str,
        word: str,
        definition: str,
        image_url: str,
        channel_name: str = "@WhiteEnglishVocabulary"
    ) -> Dict:
        """
        Create a vocabulary reel using a pre-saved template.
        
        This is more efficient as the template is stored on JSON2Video servers.
        """
        
        payload = {
            "template": template_id,
            "variables": {
                "word": word.capitalize(),
                "definition": definition,
                "image_url": image_url,
                "channel_name": channel_name,
                "voice_text": f"{word}. {definition}"
            }
        }
        
        return self._render_movie(payload)
    
    def _render_movie(self, movie_json: Dict) -> Dict:
        """Submit movie for rendering and return project info."""
        
        response = requests.post(
            f"{self.BASE_URL}/movies",
            headers=self._headers(),
            json=movie_json,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"JSON2Video API error: {response.status_code} - {response.text}")
    
    def check_status(self, project_id: str) -> Dict:
        """Check the rendering status of a project."""
        
        response = requests.get(
            f"{self.BASE_URL}/movies",
            headers=self._headers(),
            params={"project": project_id},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"JSON2Video API error: {response.status_code} - {response.text}")
    
    def wait_for_completion(self, project_id: str, timeout: int = 300, poll_interval: int = 5) -> Dict:
        """
        Wait for a movie to finish rendering.
        
        Args:
            project_id: The project ID from create_vocabulary_reel
            timeout: Maximum seconds to wait
            poll_interval: Seconds between status checks
            
        Returns:
            Dict with final status and video_url
        """
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.check_status(project_id)
            
            if status.get("status") == "done":
                return {
                    "success": True,
                    "status": "done",
                    "video_url": status.get("url"),
                    "project_id": project_id
                }
            elif status.get("status") == "error":
                return {
                    "success": False,
                    "status": "error",
                    "error": status.get("message", "Unknown error"),
                    "project_id": project_id
                }
            
            time.sleep(poll_interval)
        
        return {
            "success": False,
            "status": "timeout",
            "error": f"Rendering did not complete within {timeout} seconds",
            "project_id": project_id
        }
    
    def download_video(self, video_url: str, output_path: Path) -> Path:
        """Download the rendered video to a local file."""
        
        response = requests.get(video_url, stream=True, timeout=120)
        
        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return output_path
        else:
            raise Exception(f"Failed to download video: {response.status_code}")


def generate_vocab_video_json2video(
    word: str,
    definition: str,
    image_url: str,
    output_path: Optional[Path] = None,
    wait_for_result: bool = True
) -> Dict:
    """
    High-level function to generate a vocabulary video using JSON2Video.
    
    Args:
        word: The vocabulary word
        definition: Word definition
        image_url: URL to illustration image
        output_path: Optional local path to save the video
        wait_for_result: If True, wait for rendering to complete
        
    Returns:
        Dict with success status, video_url, and local_path if downloaded
    """
    
    client = JSON2VideoClient()
    
    # Create the video
    result = client.create_vocabulary_reel(
        word=word,
        definition=definition,
        image_url=image_url,
        channel_name=config.CHANNEL_NAME
    )
    
    project_id = result.get("project")
    
    if not wait_for_result:
        return {
            "success": True,
            "status": "rendering",
            "project_id": project_id
        }
    
    # Wait for completion
    final_result = client.wait_for_completion(project_id)
    
    if final_result.get("success") and output_path:
        # Download the video
        client.download_video(final_result["video_url"], output_path)
        final_result["local_path"] = str(output_path)
    
    return final_result


def check_json2video_status() -> Dict:
    """Check if JSON2Video API is accessible."""
    try:
        client = JSON2VideoClient()
        # Simple test - just check if we can reach the API
        response = requests.get(
            f"{client.BASE_URL}/status",
            headers=client._headers(),
            timeout=10
        )
        return {
            "available": response.status_code in [200, 401, 403],
            "api_key_set": bool(config.JSON2VIDEO_API_KEY)
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }
