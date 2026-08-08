import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
FROM_EMAIL = os.getenv("FROM_EMAIL")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

missing = []

if not GEMINI_API_KEY:
    missing.append("GEMINI_API_KEY")

if not RESEND_API_KEY:
    missing.append("RESEND_API_KEY")

if not RECIPIENT_EMAIL:
    missing.append("RECIPIENT_EMAIL")

if not FROM_EMAIL:
    missing.append("FROM_EMAIL")

if not YOUTUBE_API_KEY:
    missing.append("YOUTUBE_API_KEY")

if missing:
    raise Exception(
        f"Missing .env variables: {', '.join(missing)}"
    )
