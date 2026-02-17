#!/usr/bin/env python3
"""
Development startup script for AegisRAG.
Runs the API server with auto-reload.
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if it exists
env_file = Path(".env")
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    # Copy from .env.example if .env doesn't exist
    env_example = Path(".env.example")
    if env_example.exists():
        print(f"⚠️  .env not found. Run: cp .env.example .env")
        sys.exit(1)

# Set development defaults if not set
os.environ.setdefault("AEGIS_DEBUG", "true")
os.environ.setdefault("AEGIS_LOG_LEVEL", "DEBUG")
os.environ.setdefault("AEGIS_HOST", "127.0.0.1")
os.environ.setdefault("AEGIS_PORT", "8000")

print("""
╔═══════════════════════════════════════════════╗
║         🚀 AegisRAG Development Server        ║
╚═══════════════════════════════════════════════╝
""")

print(f"HOST: {os.getenv('AEGIS_HOST')}")
print(f"PORT: {os.getenv('AEGIS_PORT')}")
print(f"DEBUG: {os.getenv('AEGIS_DEBUG')}")
print(f"LOG_LEVEL: {os.getenv('AEGIS_LOG_LEVEL')}")
print()

# Run FastAPI server with uvicorn
cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "api.server:app",
    "--host",
    os.getenv("AEGIS_HOST", "127.0.0.1"),
    "--port",
    os.getenv("AEGIS_PORT", "8000"),
    "--reload" if os.getenv("AEGIS_DEBUG", "false").lower() == "true" else "",
]

# Remove empty strings from command
cmd = [c for c in cmd if c]

try:
    subprocess.run(cmd, check=True)
except KeyboardInterrupt:
    print("\n🛑 Server stopped")
except FileNotFoundError:
    print("❌ uvicorn not found. Install with: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
