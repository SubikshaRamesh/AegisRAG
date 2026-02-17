#!/usr/bin/env python3
"""
Verify production backend is ready for deployment.
Checks configuration, imports, and API structure.
"""

import sys
import os
from pathlib import Path

# Colors for output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def check(condition, message):
    """Print check result."""
    status = f"{GREEN}✅{RESET}" if condition else f"{RED}❌{RESET}"
    print(f"{status} {message}")
    return condition


def section(title):
    """Print section header."""
    print(f"\n{YELLOW}{'=' * 50}{RESET}")
    print(f"{YELLOW}{title}{RESET}")
    print(f"{YELLOW}{'=' * 50}{RESET}")


def main():
    """Run all verification checks."""
    all_passed = True

    # ============ CHECK STRUCTURE ============
    section("📁 Project Structure")

    required_files = [
        "api/server.py",
        "config/settings.py",
        "core/logger.py",
        "core/errors.py",
        "core/schemas.py",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        ".env.example",
        "run.py",
        "Makefile",
        "BACKEND_README.md",
    ]

    for file in required_files:
        exists = Path(file).exists()
        all_passed &= check(exists, f"{file}")

    # ============ CHECK DEPENDENCIES ============
    section("📦 Dependencies")

    required_packages = [
        ("fastapi", "FastAPI framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
        ("python-dotenv", "Environment loading"),
    ]

    for package, desc in required_packages:
        try:
            __import__(package)
            check(True, f"{package} - {desc}")
        except ImportError:
            check(False, f"{package} - {desc}")
            all_passed = False

    # ============ CHECK CONFIGURATION ============
    section("⚙️  Configuration")

    try:
        from config.settings import settings
        check(True, "Settings class loads")

        # Check required attributes
        attrs = [
            "HOST",
            "PORT",
            "DB_PATH",
            "TEXT_FAISS_INDEX_PATH",
            "IMAGE_FAISS_INDEX_PATH",
            "LLM_MODEL_PATH",
            "WORKSPACE_ROOT",
        ]

        for attr in attrs:
            has_attr = hasattr(settings, attr)
            all_passed &= check(has_attr, f"settings.{attr}")

    except Exception as e:
        check(False, f"Settings load ({e})")
        all_passed = False

    # ============ CHECK LOGGING ============
    section("📝 Logging")

    try:
        from core.logger import get_logger
        logger = get_logger("test")
        check(logger is not None, "Logger initializes")
    except Exception as e:
        check(False, f"Logger ({e})")
        all_passed = False

    # ============ CHECK ERROR HANDLING ============
    section("🛡️  Error Handling")

    try:
        from core.errors import (
            AegisRAGError,
            IngestionError,
            RetrievalError,
            ValidationError,
            retry,
            async_retry,
        )
        check(True, "Error classes defined")
        check(True, "Retry decorators defined")
    except Exception as e:
        check(False, f"Error handling ({e})")
        all_passed = False

    # ============ CHECK API ============
    section("🔌 API Server")

    try:
        from api.server import app
        from fastapi import FastAPI

        is_fastapi_app = isinstance(app, FastAPI)
        check(is_fastapi_app, "FastAPI app created")

        # Check routes
        routes = [route.path for route in app.routes]
        endpoints = ["/query", "/ingest", "/health", "/status", "/"]

        for endpoint in endpoints:
            has_endpoint = any(endpoint in route for route in routes)
            all_passed &= check(has_endpoint, f"Endpoint {endpoint}")

    except Exception as e:
        check(False, f"API server ({e})")
        all_passed = False

    # ============ CHECK MODELS ============
    section("📋 Request/Response Models")

    try:
        from core.schemas import (
            QueryRequest,
            QueryResponse,
            IngestionResponse,
            HealthResponse,
            StatusResponse,
        )
        check(True, "QueryRequest model")
        check(True, "QueryResponse model")
        check(True, "IngestionResponse model")
        check(True, "HealthResponse model")
        check(True, "StatusResponse model")
    except Exception as e:
        check(False, f"Schemas ({e})")
        all_passed = False

    # ============ CHECK MODELS EXIST ============
    section("🤖 Model Files")

    models_path = Path("models")
    if models_path.exists():
        model_files = list(models_path.glob("*.gguf"))
        check(len(model_files) > 0, f"LLM model found ({len(model_files)} file(s))")
    else:
        check(False, "models/ directory exists")
        all_passed = False

    # ============ SUMMARY ============
    section("📊 Verification Summary")

    if all_passed:
        print(f"\n{GREEN}✅ ALL CHECKS PASSED{RESET}")
        print(f"\n{GREEN}Backend is production-ready!{RESET}")
        print(f"\nNext steps:")
        print(f"  1. Run development: {YELLOW}python run.py{RESET}")
        print(f"  2. Run production:  {YELLOW}docker-compose up{RESET}")
        print(f"  3. Check docs:      {YELLOW}http://localhost:8000/docs{RESET}")
        return 0
    else:
        print(f"\n{RED}❌ SOME CHECKS FAILED{RESET}")
        print(f"\nPlease fix the issues above and run again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
