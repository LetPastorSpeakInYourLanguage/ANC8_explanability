"""Local stand-in for the Vercel Python runtime.

Serves app/api/predict.py's handler on port 8000 so the real UI can be driven
against the real scoring code during development. Vercel routes the same
handler natively, so nothing here ships.
"""
import sys
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "api"))

from predict import handler  # noqa: E402

if __name__ == "__main__":
    print("dev API on http://127.0.0.1:8000", flush=True)
    HTTPServer(("127.0.0.1", 8000), handler).serve_forever()
