#!/usr/bin/env python3
"""
Install/upgrade production dependencies.
Run this once to prepare the backend for deployment.
"""

import subprocess
import sys

print("""
╔══════════════════════════════════════════════╗
║  Installing AegisRAG Production Backend      ║
╚══════════════════════════════════════════════╝
""")

# Core dependencies for backend
deps = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "python-multipart>=0.0.6",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

print("📦 Installing FastAPI stack...")
try:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q"] + deps,
        check=True
    )
    print("✅ FastAPI stack installed")
except subprocess.CalledProcessError as e:
    print(f"❌ Installation failed: {e}")
    sys.exit(1)

print("\n✅ All production dependencies installed!")
print("\nNext steps:")
print("  1. Verify setup: python verify_backend.py")
print("  2. Run dev:      python run.py")
print("  3. Or deploy:    docker-compose up")
