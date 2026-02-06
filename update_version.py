#!/usr/bin/env python3
"""
Version Update Agent
====================
Updates version_info.json, README.md, and AI_CONTEXT.md with current git info.
Run this script after commits or before deployment.

Usage:
    python update_version.py
    python update_version.py --message "Custom update description"
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()


def run_git_command(cmd: list) -> str:
    """Run a git command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
        return result.stdout.strip()
    except Exception as e:
        print(f"Git command failed: {e}")
        return ""


def get_git_info() -> dict:
    """Get current git information."""
    branch = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    commit = run_git_command(["git", "rev-parse", "--short", "HEAD"])
    commit_full = run_git_command(["git", "rev-parse", "HEAD"])
    commit_date = run_git_command(["git", "log", "-1", "--format=%ci"])
    commit_message = run_git_command(["git", "log", "-1", "--format=%s"])
    author = run_git_command(["git", "log", "-1", "--format=%an"])
    
    return {
        "branch": branch,
        "commit": commit,
        "commit_full": commit_full,
        "commit_date": commit_date,
        "commit_message": commit_message,
        "author": author
    }


def update_version_info(git_info: dict, description: str = None) -> dict:
    """Update version_info.json file."""
    version_file = BASE_DIR / "version_info.json"
    
    # Load existing or create new
    if version_file.exists():
        with open(version_file, 'r') as f:
            data = json.load(f)
    else:
        data = {"version": "1.0.0"}
    
    # Extract version number from branch if possible (e.g., version-4 -> 4.0.0)
    version = data.get("version", "1.0.0")
    if git_info["branch"].startswith("version-"):
        try:
            v_num = git_info["branch"].split("-")[1]
            version = f"{v_num}.0.0"
        except:
            pass
    
    # Update data
    data.update({
        "branch": git_info["branch"],
        "commit": git_info["commit"],
        "commit_full": git_info["commit_full"],
        "commit_date": git_info["commit_date"],
        "commit_message": git_info["commit_message"],
        "author": git_info["author"],
        "last_updated": datetime.now().isoformat(),
        "version": version
    })
    
    if description:
        data["description"] = description
    
    # Save
    with open(version_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Updated version_info.json")
    return data


def update_readme(git_info: dict, version_data: dict):
    """Update README.md with version badge section."""
    readme_file = BASE_DIR / "README.md"
    
    if not readme_file.exists():
        print("✗ README.md not found")
        return
    
    with open(readme_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create version section
    version_section = f"""
## 📌 Version Info

| Property | Value |
|----------|-------|
| **Version** | `{version_data.get('version', 'N/A')}` |
| **Branch** | `{git_info['branch']}` |
| **Commit** | `{git_info['commit']}` |
| **Last Updated** | {git_info['commit_date']} |
| **Description** | {version_data.get('description', 'N/A')} |

"""
    
    # Check if version section exists
    if "## 📌 Version Info" in content:
        # Replace existing section
        import re
        pattern = r"## 📌 Version Info.*?(?=\n## |\Z)"
        content = re.sub(pattern, version_section.strip() + "\n\n", content, flags=re.DOTALL)
    else:
        # Add after first heading
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('# '):
                insert_pos = i + 1
                break
        
        # Find next empty line after title
        while insert_pos < len(lines) and lines[insert_pos].strip():
            insert_pos += 1
        
        lines.insert(insert_pos + 1, version_section)
        content = '\n'.join(lines)
    
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Updated README.md")


def update_ai_context(git_info: dict, version_data: dict):
    """Update AI_CONTEXT.md with current version info."""
    ai_context_file = BASE_DIR / "AI_CONTEXT.md"
    
    if not ai_context_file.exists():
        print("✗ AI_CONTEXT.md not found")
        return
    
    with open(ai_context_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create version section for AI context
    version_section = f"""
## Current Version

- **Branch**: `{git_info['branch']}`
- **Commit**: `{git_info['commit']}` ({git_info['commit_date']})
- **Version**: `{version_data.get('version', 'N/A')}`
- **Last Commit Message**: {git_info['commit_message']}
- **Description**: {version_data.get('description', 'N/A')}

"""
    
    # Check if version section exists
    if "## Current Version" in content:
        # Replace existing section
        import re
        pattern = r"## Current Version.*?(?=\n## |\Z)"
        content = re.sub(pattern, version_section.strip() + "\n\n", content, flags=re.DOTALL)
    else:
        # Add at the beginning after the title
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('# '):
                insert_pos = i + 1
                break
        
        # Skip any description text after title
        while insert_pos < len(lines) and lines[insert_pos].strip() and not lines[insert_pos].startswith('#'):
            insert_pos += 1
        
        lines.insert(insert_pos, version_section)
        content = '\n'.join(lines)
    
    with open(ai_context_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Updated AI_CONTEXT.md")


def main():
    """Main function."""
    print("=" * 50)
    print("  Version Update Agent")
    print("=" * 50)
    
    # Get custom description from command line
    description = None
    if len(sys.argv) > 2 and sys.argv[1] == "--message":
        description = sys.argv[2]
    
    # Get git info
    print("\n📋 Getting git information...")
    git_info = get_git_info()
    
    print(f"   Branch: {git_info['branch']}")
    print(f"   Commit: {git_info['commit']}")
    print(f"   Date:   {git_info['commit_date']}")
    
    # Update files
    print("\n📝 Updating files...")
    version_data = update_version_info(git_info, description)
    update_readme(git_info, version_data)
    update_ai_context(git_info, version_data)
    
    print("\n✅ Version update complete!")
    print(f"   Version: {version_data.get('version')}")
    print(f"   Branch:  {git_info['branch']}")
    print(f"   Commit:  {git_info['commit']}")
    
    return version_data


if __name__ == "__main__":
    main()
