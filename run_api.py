#!/usr/bin/env python3
"""
Startup script for Podcast Geeker API server.
"""

import os
import sys
from pathlib import Path

import uvicorn

# Add the current directory to Python path so imports work
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    # Default configuration
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "5055"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"
    reload_dirs_env = os.getenv("API_RELOAD_DIRS")

    # Limit file watchers to backend paths by default to avoid scanning the whole
    # repository (docs/assets/node_modules), which slows startup on large trees.
    if reload_dirs_env:
        reload_dirs = [path.strip() for path in reload_dirs_env.split(",") if path.strip()]
    else:
        reload_dirs = [
            str(path)
            for path in (
                current_dir / "api",
                current_dir / "open_notebook",
                current_dir / "commands",
                current_dir / "run_api.py",
            )
            if path.exists()
        ]

    print(f"Starting Podcast Geeker API server on {host}:{port}")
    print(f"Reload mode: {reload}")
    if reload:
        print(f"Reload dirs: {reload_dirs}")

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=reload_dirs if reload else None,
    )
