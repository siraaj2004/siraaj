import os
import sys
from pathlib import Path

# ============================================================
# PROJECT PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Add project root to Python path
# This allows importing:
# youtube_agent.py
# idea_generator.py
# sender.py
# config.py
sys.path.insert(0, str(BASE_DIR))


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")


# ============================================================
# CHECK API KEYS
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


if not YOUTUBE_API_KEY:
    raise ValueError(
        "YOUTUBE_API_KEY is missing.\n"
        "Add YOUTUBE_API_KEY to your .env file."
    )

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing.\n"
        "Add GEMINI_API_KEY to your .env file."
    )


# ============================================================
# IMPORT PROJECT MODULES
# ============================================================

from youtube_agent import get_trending_videos
from idea_generator import generate_report
from sender import send_email


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("YOUTUBE TREND ANALYSIS")
    print("=" * 60)

    # --------------------------------------------------------
    # STEP 1: Fetch India Trending Videos
    # --------------------------------------------------------

    print("\n[1/3] Fetching YouTube trending videos...")

    # Fetch India trends
    india_trending_data = get_trending_videos(region_code="IN", max_results=20)

    if not india_trending_data:
        raise RuntimeError(
            "YouTube returned no trending videos for India."
        )

    print(
        f"Successfully fetched {len(india_trending_data)} India trending videos."
    )

    # Fetch World trends
    world_trending_data = get_trending_videos(region_code="US", max_results=20)

    if not world_trending_data:
        raise RuntimeError(
            "YouTube returned no trending videos for World."
        )

    print(
        f"Successfully fetched {len(world_trending_data)} World trending videos."
    )


    # --------------------------------------------------------
    # STEP 2: Generate Trend Report
    # --------------------------------------------------------

   print("\n[2/3] Generating trend report...")

report = generate_report(india_trending_data, world_trending_data)

if not report:
    raise RuntimeError(
        "AI failed to generate the trend report."
    )

    print("Trend report generated successfully.")


    # --------------------------------------------------------
    # STEP 3: Send Email
    # --------------------------------------------------------

    print("\n[3/3] Sending email...")

    response = send_email(
        subject="📈 YouTube Trend Analysis Report",
        message=report
    )

    print("Email sent successfully.")

    if response:
        print(response)


    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print("\n" + "=" * 60)
        print("WORKFLOW FAILED")
        print("=" * 60)

        print(f"\nError: {error}")

        raise
