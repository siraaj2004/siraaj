import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# ==========================
# API Keys
# ==========================
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==========================
# Email Configuration
# ==========================
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# ==========================
# Validate Required Variables
# ==========================
required_vars = {
    "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "EMAIL_USER": EMAIL_USER,
    "EMAIL_PASSWORD": EMAIL_PASSWORD,
    "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
}

missing = [key for key, value in required_vars.items() if not value]

if missing:
    raise ValueError(
        "Missing environment variables in .env:\n"
        + "\n".join(f"- {var}" for var in missing)
    )