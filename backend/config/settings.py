"""Reuse the established Oscar project settings for the separated API entry point."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "sandbox"))

from settings import *  # noqa: F403,E402
