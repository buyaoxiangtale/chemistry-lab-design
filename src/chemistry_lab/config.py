"""Centralised configuration for the chemistry-lab package."""

import os

# ---------------------------------------------------------------------------
# API configuration
# ---------------------------------------------------------------------------
API_KEY_ENV = "CHEM_LAB_API_KEY"
BASE_URL_ENV = "CHEM_LAB_BASE_URL"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2000

# ---------------------------------------------------------------------------
# Default room dimensions (metres)
# ---------------------------------------------------------------------------
DEFAULT_ROOM_WIDTH_M = 6.0
DEFAULT_ROOM_DEPTH_M = 4.0

# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------
DASHSCOPE_API_KEY_ENV = "DASHSCOPE_API_KEY"
IMAGE_MODEL = "wanx2.0-t2i-turbo"
IMAGE_SIZE = "1024*1024"
IMAGE_SAVE_DIR = os.environ.get("CHEM_LAB_IMAGE_DIR", "output")
