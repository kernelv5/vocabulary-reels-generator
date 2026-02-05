# ComfyUI Client Module
# Generates images using local ComfyUI (Stable Diffusion)

import json
import requests
import time
import uuid
import urllib.parse
from pathlib import Path
from typing import Optional
import sys
sys.path.append(str(Path(__file__).parent.parent))
import config


class ComfyUIClient:
    """Client to interact with ComfyUI API."""
    
    def __init__(self, server_url: str = None):
        self.server_url = server_url or config.COMFYUI_URL
        self.client_id = str(uuid.uuid4())
    
    def is_server_running(self) -> bool:
        """Check if ComfyUI server is running."""
        try:
            response = requests.get(f"{self.server_url}/system_stats", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_available_models(self) -> list:
        """Get list of available checkpoint models."""
        try:
            response = requests.get(f"{self.server_url}/object_info/CheckpointLoaderSimple", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
            return []
        except Exception:
            return []
    
    def queue_prompt(self, workflow: dict) -> str:
        """Queue a workflow and return prompt_id."""
        payload = {"prompt": workflow, "client_id": self.client_id}
        response = requests.post(f"{self.server_url}/prompt", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get("prompt_id")
        raise Exception(f"Failed to queue prompt: {response.text}")
    
    def get_history(self, prompt_id: str) -> dict:
        """Get execution history for a prompt."""
        response = requests.get(f"{self.server_url}/history/{prompt_id}", timeout=10)
        return response.json() if response.status_code == 200 else {}
    
    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Download generated image."""
        params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
        response = requests.get(f"{self.server_url}/view?{params}", timeout=30)
        if response.status_code == 200:
            return response.content
        raise Exception(f"Failed to get image: {response.status_code}")
    
    def wait_for_completion(self, prompt_id: str, timeout: int = 180) -> dict:
        """Wait for prompt to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(1)
        raise TimeoutError(f"Prompt did not complete within {timeout}s")
    
    def generate_image(self, prompt: str, negative_prompt: str = "",
                       output_path: Optional[Path] = None,
                       model: str = None, width: int = None, height: int = None,
                       steps: int = None, cfg: float = None, seed: int = None) -> Path:
        """Generate an image from text prompt."""
        model = model or config.COMFYUI_MODEL
        width = width or config.IMAGE_WIDTH
        height = height or config.IMAGE_HEIGHT
        steps = steps or config.IMAGE_STEPS
        cfg = cfg or config.IMAGE_CFG
        seed = seed if seed is not None else int(time.time() * 1000) % (2**32)
        negative_prompt = negative_prompt or config.IMAGE_NEGATIVE_PROMPT
        
        workflow = self._build_workflow(prompt, negative_prompt, model, width, height, steps, cfg, seed)
        prompt_id = self.queue_prompt(workflow)
        result = self.wait_for_completion(prompt_id)
        
        outputs = result.get("outputs", {})
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for image_info in node_output["images"]:
                    image_data = self.get_image(image_info["filename"], image_info.get("subfolder", ""))
                    
                    if output_path is None:
                        output_path = config.TEMP_DIR / f"image_{prompt_id}.png"
                    
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(image_data)
                    return output_path
        
        raise Exception("No image was generated")
    
    def _build_workflow(self, prompt: str, negative_prompt: str, model: str,
                        width: int, height: int, steps: int, cfg: float, seed: int) -> dict:
        """Build ComfyUI workflow for SDXL image generation."""
        return {
            "3": {
                "inputs": {
                    "seed": seed, "steps": steps, "cfg": cfg,
                    "sampler_name": "dpmpp_sde", "scheduler": "karras",
                    "denoise": 1, "model": ["4", 0], "positive": ["6", 0],
                    "negative": ["7", 0], "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {"inputs": {"ckpt_name": model}, "class_type": "CheckpointLoaderSimple"},
            "5": {"inputs": {"width": width, "height": height, "batch_size": 1}, "class_type": "EmptyLatentImage"},
            "6": {"inputs": {"text": prompt, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
            "7": {"inputs": {"text": negative_prompt, "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
            "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
            "9": {"inputs": {"filename_prefix": "vocab_image", "images": ["8", 0]}, "class_type": "SaveImage"}
        }


def generate_vocab_image(word: str, definition: str, output_path: Path) -> Path:
    """Generate illustration for a vocabulary word."""
    client = ComfyUIClient()
    
    if not client.is_server_running():
        raise ConnectionError(f"ComfyUI server is not running at {config.COMFYUI_URL}")
    
    prompt = config.IMAGE_PROMPT_TEMPLATE.format(word=word, definition=definition)
    return client.generate_image(prompt=prompt, output_path=output_path)


def check_comfyui_status() -> dict:
    """Check ComfyUI server status."""
    client = ComfyUIClient()
    running = client.is_server_running()
    models = client.get_available_models() if running else []
    return {
        "running": running,
        "url": config.COMFYUI_URL,
        "models": models,
        "current_model": config.COMFYUI_MODEL,
        "model_available": config.COMFYUI_MODEL in models if models else False
    }
