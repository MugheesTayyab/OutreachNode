import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if it exists
dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path, override=True)
else:
    load_dotenv(override=True)

# API Keys & Credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Config Parameters
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")
MAX_RETRIES = 3

# Paths
INPUT_DIR = BASE_DIR / 'data' / 'input'
OUTPUT_DIR = BASE_DIR / 'data' / 'output'
AUDIO_DIR = BASE_DIR / 'static' / 'audio'

# Ensure directories exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
