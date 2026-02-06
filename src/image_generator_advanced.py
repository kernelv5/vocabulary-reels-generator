"""
Advanced Image Generator with Background Removal and Customization
"""

import json
import requests
import time
import uuid
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.layout_config import get_layout_config

class AdvancedImageGenerator:
    """
    Enhanced image generator with:
    - Customizable prompts, seeds, steps, etc.
    - Background removal for transparency
    - Layout-aware sizing
    """
    
    def __init__(self, comfyui_url: str = None):
        layout = get_layout_config()
        
        # Get ComfyUI URL from environment or use default
        import os
        self.comfyui_url = comfyui_url or os.environ.get("COMFYUI_URL", "http://host.docker.internal:8188")
        self.client_id = str(uuid.uuid4())
        
        # Image generation defaults from layout config
        # Check if we should use layout element size instead of fixed size
        use_layout_size = layout.config.get('image_generation', {}).get('use_layout_size', False)
        
        if use_layout_size:
            # Use the image element's display area dimensions
            img_elem = layout.image
            self.default_width = img_elem.get('max_width', 750)
            self.default_height = img_elem.get('height', 225)
        else:
            # Use fixed dimensions from image_generation config
            self.default_width = layout.image_width
            self.default_height = layout.image_height
        
        self.default_steps = layout.image_steps
        self.default_cfg = layout.image_cfg_scale
        self.default_seed = layout.image_seed
    
    def is_server_running(self) -> bool:
        """Check if ComfyUI server is running."""
        try:
            response = requests.get(f"{self.comfyui_url}/system_stats", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def generate_image(self, 
                      word: str,
                      definition: str,
                      output_path: Path,
                      prompt_image_guideline: str = None,
                      custom_prompt: Optional[str] = None,
                      custom_negative: Optional[str] = None,
                      seed: int = -1,
                      steps: int = None,
                      cfg_scale: float = None,
                      width: int = None,
                      height: int = None,
                      sampler: str = "euler_ancestral",
                      remove_background: bool = True) -> Dict[str, Any]:
        """
        Generate image with full customization.
        
        Args:
            word: Vocabulary word
            definition: Word definition (used for display, fallback for image prompt)
            output_path: Where to save final image
            prompt_image_guideline: Custom guideline for image generation (overrides definition)
            custom_prompt: Override default prompt template
            custom_negative: Override default negative prompt
            seed: Random seed (-1 for random)
            steps: Number of diffusion steps
            cfg_scale: CFG scale
            width: Image width
            height: Image height
            sampler: Sampler name
            remove_background: Whether to remove background for transparency
        
        Returns:
            Dict with success status, paths, and metadata
        """
        layout = get_layout_config()
        
        # Use prompt_image_guideline if provided, otherwise fall back to definition
        image_prompt_content = prompt_image_guideline.strip() if prompt_image_guideline and prompt_image_guideline.strip() else definition
        
        # Use parameters or defaults
        width = width or self.default_width
        height = height or self.default_height
        steps = steps or self.default_steps
        cfg_scale = cfg_scale or self.default_cfg
        
        # Generate seed if random
        if seed == -1:
            seed = int(time.time() * 1000) % (2**32)
        
        # Build prompts - use prompt_image_guideline for image generation
        if custom_prompt:
            prompt = custom_prompt.format(word=word, prompt_image_guideline=image_prompt_content, definition=definition)
        else:
            prompt = layout.get_image_prompt(word, image_prompt_content)
        
        if custom_negative:
            negative_prompt = custom_negative
        else:
            negative_prompt = layout.image_negative_prompt
        
        try:
            # Generate image with ComfyUI
            temp_path = output_path.parent / f"temp_{output_path.name}"
            
            workflow = self._build_workflow(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg_scale,
                seed=seed,
                sampler=sampler
            )
            
            # Queue and wait
            prompt_id = self._queue_prompt(workflow)
            result = self._wait_for_completion(prompt_id)
            
            # Download image
            image_data = self._extract_image_from_result(result)
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            
            # Remove background if requested
            final_path = output_path
            if remove_background and layout.background_removal_enabled:
                final_path = self._remove_background(temp_path, output_path)
                temp_path.unlink()  # Clean up temp
            else:
                temp_path.rename(output_path)
            
            return {
                "success": True,
                "image_path": str(final_path),
                "seed": seed,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "sampler": sampler,
                "background_removed": remove_background
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _remove_background(self, input_path: Path, output_path: Path) -> Path:
        """
        Remove background from image to make it transparent.
        
        Args:
            input_path: Source image
            output_path: Destination for transparent image
        
        Returns:
            Path to output image
        """
        try:
            # Try using rembg library
            from rembg import remove
            
            with open(input_path, 'rb') as f:
                input_data = f.read()
            
            output_data = remove(input_data)
            
            with open(output_path, 'wb') as f:
                f.write(output_data)
            
            return output_path
            
        except ImportError:
            print("Warning: rembg not installed. Using simple color-based removal.")
            # Fallback: simple white background removal
            return self._remove_white_background(input_path, output_path)
    
    def _remove_white_background(self, input_path: Path, output_path: Path, 
                                 threshold: int = 240) -> Path:
        """
        Simple white background removal by color threshold.
        
        Args:
            input_path: Source image
            output_path: Destination
            threshold: RGB threshold for "white" (0-255)
        
        Returns:
            Path to output image
        """
        img = Image.open(input_path).convert("RGBA")
        data = img.getdata()
        
        new_data = []
        for item in data:
            # If pixel is mostly white, make it transparent
            if item[0] > threshold and item[1] > threshold and item[2] > threshold:
                new_data.append((255, 255, 255, 0))  # Transparent
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        img.save(output_path, "PNG")
        
        return output_path
    
    def _build_workflow(self, prompt: str, negative_prompt: str,
                       width: int, height: int, steps: int, cfg: float, 
                       seed: int, sampler: str) -> dict:
        """Build ComfyUI workflow."""
        # Get model from environment or use default
        import os
        model = os.environ.get("COMFYUI_MODEL", "DreamShaperXL_Lightning.safetensors")
        
        return {
            "3": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": sampler,
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {"ckpt_name": model},
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "vocab_transparent",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }
    
    def _queue_prompt(self, workflow: dict) -> str:
        """Queue workflow and return prompt ID."""
        payload = {"prompt": workflow, "client_id": self.client_id}
        response = requests.post(f"{self.comfyui_url}/prompt", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get("prompt_id")
        raise Exception(f"Failed to queue: {response.text}")
    
    def _wait_for_completion(self, prompt_id: str, timeout: int = 180) -> dict:
        """Wait for completion."""
        start = time.time()
        while time.time() - start < timeout:
            response = requests.get(f"{self.comfyui_url}/history/{prompt_id}", timeout=10)
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    return history[prompt_id]
            time.sleep(1)
        raise TimeoutError(f"Timeout after {timeout}s")
    
    def _extract_image_from_result(self, result: dict) -> bytes:
        """Extract image data from result."""
        outputs = result.get("outputs", {})
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for image_info in node_output["images"]:
                    filename = image_info["filename"]
                    subfolder = image_info.get("subfolder", "")
                    params = urllib.parse.urlencode({
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": "output"
                    })
                    response = requests.get(f"{self.comfyui_url}/view?{params}", timeout=30)
                    if response.status_code == 200:
                        return response.content
        raise Exception("No image found in result")


# Convenience function
def generate_vocab_image_advanced(word: str, definition: str, output_path: Path, **kwargs) -> Dict[str, Any]:
    """
    Generate vocabulary image with advanced options.
    
    Args:
        word: Vocabulary word
        definition: Definition
        output_path: Output file path
        **kwargs: Additional parameters (seed, steps, cfg_scale, etc.)
    
    Returns:
        Result dictionary
    """
    generator = AdvancedImageGenerator()
    
    if not generator.is_server_running():
        return {
            "success": False,
            "error": f"ComfyUI server not running at {generator.comfyui_url}"
        }
    
    return generator.generate_image(word, definition, output_path, **kwargs)
