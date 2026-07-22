from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Email
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# Optional: Validate required variables
required_vars = {
    "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
    "RESEND_API_KEY": RESEND_API_KEY,
    "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
}

missing = [name for name, value in required_vars.items() if not value]

if missing:
    raise ValueError(
        f"Missing environment variables: {', '.join(missing)}"
    )
