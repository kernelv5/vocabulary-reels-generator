# CSV Reader Module
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import sys
sys.path.append(str(Path(__file__).parent.parent))
import config


def load_vocabulary(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """Load vocabulary from CSV file."""
    csv_path = csv_path or config.CSV_FILE
    
    if not csv_path.exists():
        # Create empty DataFrame with required columns
        df = pd.DataFrame(columns=[
            config.COL_WORD, config.COL_DEFINITION, 
            config.COL_EXAMPLE, config.COL_PROMPT_IMAGE,
            config.COL_STATUS, config.COL_VIDEO_PATH
        ])
        df.to_csv(csv_path, index=False)
        return df
    
    df = pd.read_csv(csv_path)
    
    # Ensure required columns exist
    if config.COL_STATUS not in df.columns:
        df[config.COL_STATUS] = "pending"
    if config.COL_VIDEO_PATH not in df.columns:
        df[config.COL_VIDEO_PATH] = ""
    if config.COL_EXAMPLE not in df.columns:
        df[config.COL_EXAMPLE] = ""
    if config.COL_PROMPT_IMAGE not in df.columns:
        df[config.COL_PROMPT_IMAGE] = ""
    
    # Fill NaN values
    df[config.COL_STATUS] = df[config.COL_STATUS].fillna("pending")
    df[config.COL_VIDEO_PATH] = df[config.COL_VIDEO_PATH].fillna("")
    df[config.COL_EXAMPLE] = df[config.COL_EXAMPLE].fillna("")
    df[config.COL_PROMPT_IMAGE] = df[config.COL_PROMPT_IMAGE].fillna("")
    
    return df


def save_vocabulary(df: pd.DataFrame, csv_path: Optional[Path] = None):
    """Save vocabulary to CSV file."""
    csv_path = csv_path or config.CSV_FILE
    df.to_csv(csv_path, index=False)


def add_word(word: str, definition: str, example: str = "", prompt_image_guideline: str = "") -> int:
    """Add a new word to the vocabulary. Returns the index."""
    df = load_vocabulary()
    
    new_row = {
        config.COL_WORD: word,
        config.COL_DEFINITION: definition,
        config.COL_EXAMPLE: example,
        config.COL_PROMPT_IMAGE: prompt_image_guideline,
        config.COL_STATUS: "pending",
        config.COL_VIDEO_PATH: ""
    }
    
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_vocabulary(df)
    
    return len(df) - 1


def get_pending_words(df: pd.DataFrame) -> pd.DataFrame:
    """Get words that haven't been processed."""
    return df[df[config.COL_STATUS] != "completed"]


def get_word_by_index(index: int) -> Optional[Dict]:
    """Get word data by index."""
    df = load_vocabulary()
    if index < 0 or index >= len(df):
        return None
    
    row = df.iloc[index]
    return {
        "index": index,
        "word": str(row[config.COL_WORD]),
        "definition": str(row[config.COL_DEFINITION]),
        "example": str(row.get(config.COL_EXAMPLE, "")),
        "prompt_image_guideline": str(row.get(config.COL_PROMPT_IMAGE, "")),
        "status": str(row.get(config.COL_STATUS, "pending")),
        "video_path": str(row.get(config.COL_VIDEO_PATH, ""))
    }


def update_word_status(index: int, status: str, video_path: str = ""):
    """Update word status."""
    df = load_vocabulary()
    if 0 <= index < len(df):
        df.at[index, config.COL_STATUS] = status
        if video_path:
            df.at[index, config.COL_VIDEO_PATH] = video_path
        save_vocabulary(df)


def delete_word(index: int) -> bool:
    """Delete a word by index."""
    df = load_vocabulary()
    if 0 <= index < len(df):
        df = df.drop(index).reset_index(drop=True)
        save_vocabulary(df)
        return True
    return False


def get_all_words() -> List[Dict]:
    """Get all words as list of dicts."""
    df = load_vocabulary()
    words = []
    for idx, row in df.iterrows():
        words.append({
            "index": idx,
            "word": str(row[config.COL_WORD]),
            "definition": str(row[config.COL_DEFINITION]),
            "example": str(row.get(config.COL_EXAMPLE, "")),
            "prompt_image_guideline": str(row.get(config.COL_PROMPT_IMAGE, "")),
            "status": str(row.get(config.COL_STATUS, "pending")),
            "video_path": str(row.get(config.COL_VIDEO_PATH, ""))
        })
    return words


def clear_all_words():
    """Clear all vocabulary data."""
    df = pd.DataFrame(columns=[
        config.COL_WORD, config.COL_DEFINITION, 
        config.COL_EXAMPLE, config.COL_STATUS, config.COL_VIDEO_PATH
    ])
    save_vocabulary(df)
