from dotenv import load_dotenv
import os

load_dotenv()

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

missing = []

if not SMTP_EMAIL:
    missing.append("SMTP_EMAIL")

if not SMTP_PASSWORD:
    missing.append("SMTP_PASSWORD")

if not RECIPIENT_EMAIL:
    missing.append("RECIPIENT_EMAIL")

if missing:
    raise Exception(
        f"Missing .env variables: {', '.join(missing)}"
    )
