"""
Central configuration for YouTube Trend Analysis
================================================

Location:
    project_root/config.py

Loads:
    .env

Required:
    YOUTUBE_API_KEY
    GEMINI_API_KEY
    RESEND_API_KEY
    FROM_EMAIL
    RECIPIENT_EMAIL
"""

from pathlib import Path
import os

from dotenv import load_dotenv


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

ENV_FILE = PROJECT_ROOT / ".env"


# ============================================================
# LOAD .ENV
# ============================================================

if ENV_FILE.exists():

    load_dotenv(
        dotenv_path=ENV_FILE,
        override=False
    )

else:

    print(f"⚠️ WARNING: .env not found at:")
    print(ENV_FILE)


# ============================================================
# API CONFIGURATION
# ============================================================

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    ""
).strip()


GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()


# ============================================================
# RESEND EMAIL CONFIGURATION
# ============================================================

RESEND_API_KEY = os.getenv(
    "RESEND_API_KEY",
    ""
).strip()


FROM_EMAIL = os.getenv(
    "FROM_EMAIL",
    ""
).strip()


RECIPIENT_EMAIL = os.getenv(
    "RECIPIENT_EMAIL",
    ""
).strip()


# ============================================================
# VALIDATION
# ============================================================

def validate_config():

    required = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    if missing:

        print()
        print("=" * 70)
        print("❌ CONFIGURATION ERROR")
        print("=" * 70)

        print("\nMissing environment variables:")

        for name in missing:
            print(f"  - {name}")

        print("\nExpected .env location:")
        print(ENV_FILE)

        return False

    return True


# ============================================================
# DEBUG
# ============================================================

def print_config_status():

    print()
    print("=" * 70)
    print("CONFIGURATION STATUS")
    print("=" * 70)

    print(
        f"YOUTUBE_API_KEY : "
        f"{'✓ Found' if YOUTUBE_API_KEY else '❌ Missing'}"
    )

    print(
        f"GEMINI_API_KEY  : "
        f"{'✓ Found' if GEMINI_API_KEY else '❌ Missing'}"
    )

    print(
        f"RESEND_API_KEY  : "
        f"{'✓ Found' if RESEND_API_KEY else '❌ Missing'}"
    )

    print(
        f"FROM_EMAIL      : "
        f"{'✓ Found' if FROM_EMAIL else '❌ Missing'}"
    )

    print(
        f"RECIPIENT_EMAIL : "
        f"{'✓ Found' if RECIPIENT_EMAIL else '❌ Missing'}"
    )


# ============================================================
# TEST CONFIG
# ============================================================

if __name__ == "__main__":

    print(f"Project root: {PROJECT_ROOT}")

    print(f".env file   : {ENV_FILE}")

    print_config_status()

    if validate_config():

        print("\n✅ Configuration is valid.")

    else:

        print("\n❌ Configuration is incomplete.")
