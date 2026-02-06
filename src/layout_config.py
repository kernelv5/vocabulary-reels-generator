"""
Layout Manager - Load and manage layout configuration from JSON
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

class LayoutConfig:
    """Manages layout configuration from JSON file."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize layout configuration.
        
        Args:
            config_path: Path to layout_config.json. If None, uses default location.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "layout_config.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Layout config not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def reload(self):
        """Reload configuration from file."""
        self.config = self._load_config()
    
    def save(self, new_config: Dict[str, Any] = None):
        """
        Save configuration to file.
        
        Args:
            new_config: If provided, saves this config. Otherwise saves current.
        """
        config_to_save = new_config if new_config is not None else self.config
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        
        if new_config is not None:
            self.config = new_config
    
    # Canvas properties
    @property
    def canvas_width(self) -> int:
        return self.config['canvas']['width']
    
    @property
    def canvas_height(self) -> int:
        return self.config['canvas']['height']
    
    @property
    def canvas_size(self) -> Tuple[int, int]:
        return (self.canvas_width, self.canvas_height)
    
    @property
    def background_color(self) -> Tuple[int, int, int]:
        """Return RGB tuple for background color."""
        return tuple(self.config['canvas']['background_color'])
    
    # Safe area
    @property
    def safe_left(self) -> int:
        return self.config['safe_area']['left']
    
    @property
    def safe_right(self) -> int:
        return self.config['safe_area']['right']
    
    @property
    def safe_width(self) -> int:
        return self.config['safe_area']['width']
    
    @property
    def safe_center_x(self) -> int:
        """Return X coordinate of safe area center."""
        return self.safe_left + (self.safe_width // 2)
    
    # Typography
    @property
    def font_family(self) -> str:
        return self.config['typography']['font_family']
    
    @property
    def fallback_fonts(self) -> list:
        return self.config['typography']['fallback_fonts']
    
    # Element getters
    def get_element(self, element_name: str) -> Dict[str, Any]:
        """Get configuration for a specific element."""
        return self.config['elements'].get(element_name, {})
    
    @property
    def word_title(self) -> Dict[str, Any]:
        return self.get_element('word_title')
    
    @property
    def definition(self) -> Dict[str, Any]:
        return self.get_element('definition')
    
    @property
    def image(self) -> Dict[str, Any]:
        return self.get_element('image')
    
    @property
    def branding(self) -> Dict[str, Any]:
        return self.get_element('branding')
    
    # Image generation settings
    @property
    def image_gen(self) -> Dict[str, Any]:
        return self.config['image_generation']
    
    def get_image_prompt(self, word: str, prompt_image_guideline: str) -> str:
        """Generate image prompt with word and prompt_image_guideline."""
        template = self.image_gen['prompt_template']
        return template.format(word=word, prompt_image_guideline=prompt_image_guideline)
    
    @property
    def image_negative_prompt(self) -> str:
        return self.image_gen['negative_prompt']
    
    @property
    def image_width(self) -> int:
        return self.image_gen['width']
    
    @property
    def image_height(self) -> int:
        return self.image_gen['height']
    
    @property
    def image_steps(self) -> int:
        return self.image_gen['steps']
    
    @property
    def image_cfg_scale(self) -> float:
        return self.image_gen['cfg_scale']
    
    @property
    def image_seed(self) -> int:
        return self.image_gen['seed']
    
    @property
    def background_removal_enabled(self) -> bool:
        return self.image_gen['background_removal']['enabled']
    
    # Video settings
    @property
    def video_fps(self) -> int:
        return self.config['video']['fps']
    
    @property
    def video_duration(self) -> int:
        return self.config['video']['duration_seconds']
    
    @property
    def video_format(self) -> str:
        return self.config['video']['format']
    
    # Branding
    @property
    def channel_name(self) -> str:
        return self.config['branding']['channel_name']
    
    @property
    def show_branding(self) -> bool:
        return self.config['branding']['show_branding']
    
    # Utility methods
    def get_color_rgb(self, element_name: str) -> Tuple[int, int, int]:
        """Get RGB color tuple for an element."""
        element = self.get_element(element_name)
        return tuple(element.get('color', [0, 0, 0]))
    
    def update_element(self, element_name: str, updates: Dict[str, Any]):
        """
        Update specific properties of an element.
        
        Args:
            element_name: Name of element to update
            updates: Dictionary of properties to update
        """
        if element_name in self.config['elements']:
            self.config['elements'][element_name].update(updates)
    
    def update_image_gen(self, updates: Dict[str, Any]):
        """Update image generation settings."""
        self.config['image_generation'].update(updates)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return full configuration as dictionary."""
        return self.config.copy()


# Global instance for easy access
_layout_config = None

def get_layout_config(config_path: Optional[Path] = None) -> LayoutConfig:
    """
    Get global layout configuration instance.
    
    Args:
        config_path: Optional path to config file. Only used on first call.
    
    Returns:
        LayoutConfig instance
    """
    global _layout_config
    if _layout_config is None:
        _layout_config = LayoutConfig(config_path)
    return _layout_config


def reload_layout_config():
    """Reload configuration from file."""
    global _layout_config
    if _layout_config is not None:
        _layout_config.reload()
