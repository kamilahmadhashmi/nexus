"""
Vercel serverless function entrypoint for NEXUS.
Exposes the FastAPI ASGI app for Vercel's Python runtime.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.main import app
