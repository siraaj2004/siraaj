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
from idea_generator import generate_ideas
from sender import send_email


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("YOUTUBE TREND ANALYSIS")
    print("=" * 60)

    # --------------------------------------------------------
    # STEP 1: Fetch India Trends
    # --------------------------------------------------------

    print("\n[1/3] Fetching YouTube trending videos...")

    india_trends = get_trending_videos(region_code="IN", max_results=20)

    if not india_trends:
        raise RuntimeError(
            "YouTube returned no trending videos for India."
        )

    print(
        f"Successfully fetched {len(india_trends)} India trending videos."
    )

    # --------------------------------------------------------
    # STEP 1B: Fetch World Trends
    # --------------------------------------------------------

    print("\nFetching world YouTube trending videos...")

    world_trends = get_trending_videos(region_code="US", max_results=20)

    if not world_trends:
        raise RuntimeError(
            "YouTube returned no trending videos for world."
        )

    print(
        f"Successfully fetched {len(world_trends)} world trending videos."
    )


    # --------------------------------------------------------
    # STEP 2
    # --------------------------------------------------------

    print("\n[2/3] Generating trend report...")

    report = generate_ideas(india_trends, world_trends)

    if not report:
        raise RuntimeError(
            "AI failed to generate the trend report."
        )

    print("Trend report generated successfully.")


    # --------------------------------------------------------
    # STEP 3
    # --------------------------------------------------------

    print("\n[3/3] Sending email...")

    response = send_email(
        subject="📈 YouTube Trend Analysis Report",
        body=report
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
