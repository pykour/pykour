"""Simple example application for Pykour.

Run with: uvicorn examples.app:app --reload

Routes:
  GET  /       - Index endpoint
  GET  /health - Health check
  POST /echo   - Echo request details
"""

from pathlib import Path

from pykour import Pykour

app = Pykour(routes_dir=Path(__file__).parent / "routes")
