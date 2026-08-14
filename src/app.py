import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ============================================================
# PROJECT PATH & ENV LOADING
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from root directory (where workflow creates it)
env_file = BASE_DIR / ".env"
load_dotenv(env_file)

# Verify required environment variables are loaded
required_env_vars = [
    "YOUTUBE_API_KEY",
    "GEMINI_API_KEY",
    "RECIPIENT_EMAIL",
    "FROM_EMAIL",
    "RESEND_API_KEY"
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        f"Expected .env file at: {env_file}"
    )

# Allow app.py to import idea_generator.py from project root
sys.path.insert(0, str(BASE_DIR))

# ============================================================
# IMPORT IDEA GENERATOR
# ============================================================

from idea_generator import (
    get_india_trends,
    get_world_trends,
    generate_report,
    clean_report,
    create_pdf,
    save_raw_report,
    send_pdf_email,
)


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# MAIN TRIGGER
# ============================================================

def main():

    print()
    print("=" * 60)
    print("       YOUTUBE TREND INTELLIGENCE AGENT")
    print("=" * 60)

    try:

        # ----------------------------------------------------
        # STEP 1 — INDIA TRENDS
        # ----------------------------------------------------

        print()
        print("[1/6] Collecting India YouTube trends...")

        india_trends = get_india_trends()

        print(
            f"India trends collected: "
            f"{len(india_trends)}"
        )

        if not india_trends:
            raise RuntimeError(
                "No India YouTube trend data found."
            )

        # ----------------------------------------------------
        # STEP 2 — WORLD TRENDS
        # ----------------------------------------------------

        print()
        print("[2/6] Collecting global YouTube trends...")

        world_trends = get_world_trends()

        print(
            f"World trends collected: "
            f"{len(world_trends)}"
        )

        if not world_trends:
            raise RuntimeError(
                "No World YouTube trend data found."
            )

        # ----------------------------------------------------
        # STEP 3 — GEMINI REPORT
        # ----------------------------------------------------

        print()
        print("[3/6] Generating YouTube trend report...")

        report = generate_report(
            india_trends,
            world_trends
        )

        report = clean_report(report)

        if not report:
            raise RuntimeError(
                "Generated report is empty."
            )

        print("Report generated successfully.")

        # ----------------------------------------------------
        # STEP 4 — SAVE RAW REPORT
        # ----------------------------------------------------

        print()
        print("[4/6] Saving raw report...")

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        raw_file = (
            OUTPUT_DIR
            / f"youtube_trend_report_{timestamp}.txt"
        )

        save_raw_report(
            report,
            str(raw_file)
        )

        print(
            f"Raw report saved:\n{raw_file}"
        )

        # ----------------------------------------------------
        # STEP 5 — CREATE PDF
        # ----------------------------------------------------

        print()
        print("[5/6] Creating PDF...")

        pdf_file = (
            OUTPUT_DIR
            / f"YouTube_Trend_Intelligence_{timestamp}.pdf"
        )

        create_pdf(
            report,
            str(pdf_file)
        )

        if not pdf_file.exists():
            raise RuntimeError(
                "PDF was not created."
            )

        print(
            f"PDF created successfully:\n{pdf_file}"
        )

        # ----------------------------------------------------
        # STEP 6 — SEND EMAIL
        # ----------------------------------------------------

        print()
        print("[6/6] Sending PDF to Gmail...")

        send_pdf_email(
            str(pdf_file)
        )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("             COMPLETED SUCCESSFULLY")
        print("=" * 60)

        print()
        print(f"PDF: {pdf_file}")
        print()
        print("The PDF report has been sent to your email.")
        print()

    except Exception as error:

        print()
        print("=" * 60)
        print("                 FAILED")
        print("=" * 60)

        print()
        print(f"Error: {error}")
        print()

        raise


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
