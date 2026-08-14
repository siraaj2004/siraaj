"""
YouTube Trend Analysis - MAIN TRIGGER
=====================================

Run:

    python src/app.py

Pipeline:

    1. Load .env
    2. Validate API keys and email configuration
    3. Run YouTube analysis
    4. Run idea generator if available
    5. Generate PDF
    6. Find newest PDF
    7. Send PDF directly through Resend
    8. Finish

No sender.py dependency.
No config.py dependency.
"""

from __future__ import annotations

import os
import sys
import subprocess
import base64
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv


# ============================================================
# PATH CONFIGURATION
# ============================================================

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

os.chdir(PROJECT_ROOT)

print("=" * 70)
print("       YOUTUBE TREND INTELLIGENCE GENERATOR")
print("=" * 70)

print()
print("Project root:")
print(PROJECT_ROOT)

print()
print("Source folder:")
print(SRC_DIR)


# ============================================================
# LOAD .ENV
# ============================================================

ENV_FILE = PROJECT_ROOT / ".env"

print()
print("Looking for .env:")
print(ENV_FILE)

if not ENV_FILE.exists():

    print()
    print("❌ ERROR: .env file not found.")
    print()
    print("Expected:")
    print(ENV_FILE)

    sys.exit(1)


load_dotenv(ENV_FILE)

print("✓ .env loaded successfully")


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    ""
).strip()

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

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
# CHECK ENVIRONMENT
# ============================================================

print()
print("=" * 70)
print("CHECKING ENVIRONMENT VARIABLES")
print("=" * 70)


environment = {
    "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "RESEND_API_KEY": RESEND_API_KEY,
    "FROM_EMAIL": FROM_EMAIL,
    "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
}


missing = []


for name, value in environment.items():

    if value:

        print(f"✓ {name} found")

    else:

        print(f"❌ {name} missing")

        missing.append(name)


if missing:

    print()
    print("=" * 70)
    print("❌ MISSING ENVIRONMENT VARIABLES")
    print("=" * 70)

    for name in missing:

        print(f"  - {name}")

    sys.exit(1)


# ============================================================
# RUN PYTHON SCRIPT
# ============================================================

def run_script(
    script: Path,
    description: str,
    required: bool = True
) -> bool:

    if not script.exists():

        print()
        print(f"⚠️ Script not found:")
        print(script)

        if required:

            print("❌ Required script is missing.")

            return False

        print("Optional script. Skipping.")

        return True


    print()
    print("=" * 70)
    print(description)
    print("=" * 70)

    print()
    print("Running:")
    print(script)


    try:

        result = subprocess.run(
            [
                sys.executable,
                str(script)
            ],
            cwd=str(PROJECT_ROOT),
            env=os.environ.copy(),
            check=False
        )


    except Exception as exc:

        print()
        print("❌ ERROR RUNNING SCRIPT")

        print(
            f"{type(exc).__name__}: {exc}"
        )

        return False


    if result.returncode != 0:

        print()
        print(
            f"❌ {script.name} failed "
            f"with exit code {result.returncode}"
        )

        return False


    print()
    print(f"✓ {description} completed successfully.")

    return True


# ============================================================
# FIND PDF FILES
# ============================================================

def find_pdfs() -> list[Path]:

    locations = [

        PROJECT_ROOT,

        PROJECT_ROOT / "reports",

        PROJECT_ROOT / "output",

        PROJECT_ROOT / "generated",

        PROJECT_ROOT / "pdf",

        SRC_DIR,

    ]


    pdfs = []


    for location in locations:

        if not location.exists():

            continue


        try:

            for pdf in location.glob("*.pdf"):

                if pdf.is_file():

                    if pdf not in pdfs:

                        pdfs.append(pdf)


        except Exception:

            pass


    return sorted(
        pdfs,
        key=lambda file: file.stat().st_mtime,
        reverse=True
    )


# ============================================================
# SEND EMAIL WITH PDF
# ============================================================

def send_report_email(pdf_path: Path) -> bool:

    print()
    print("=" * 70)
    print("SENDING PDF REPORT BY EMAIL")
    print("=" * 70)


    if not pdf_path.exists():

        print()
        print("❌ PDF does not exist:")
        print(pdf_path)

        return False


    print()
    print(f"PDF: {pdf_path}")

    print(
        f"Size: "
        f"{pdf_path.stat().st_size:,} bytes"
    )


    # --------------------------------------------------------
    # Read PDF
    # --------------------------------------------------------

    try:

        with open(
            pdf_path,
            "rb"
        ) as file:

            pdf_bytes = file.read()


    except Exception as exc:

        print()
        print("❌ Could not read PDF.")

        print(exc)

        return False


    # --------------------------------------------------------
    # Convert PDF to Base64
    # --------------------------------------------------------

    pdf_base64 = base64.b64encode(
        pdf_bytes
    ).decode("utf-8")


    # --------------------------------------------------------
    # Resend API
    # --------------------------------------------------------

    url = "https://api.resend.com/emails"


    headers = {

        "Authorization":
            f"Bearer {RESEND_API_KEY}",

        "Content-Type":
            "application/json",
    }


    payload = {

        "from":
            FROM_EMAIL,

        "to":
            [RECIPIENT_EMAIL],

        "subject":
            "YouTube Trend Analysis Report",

        "html":
            """
            <h2>YouTube Trend Analysis</h2>

            <p>
            Your latest YouTube Trend Analysis report
            has been generated successfully.
            </p>

            <p>
            The PDF report is attached to this email.
            </p>

            <p>
            Generated automatically by GitHub Actions.
            </p>
            """,

        "attachments": [

            {

                "filename":
                    pdf_path.name,

                "content":
                    pdf_base64,
            }

        ],
    }


    print()
    print("Sending through Resend...")

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )


    except requests.RequestException as exc:

        print()
        print("❌ Resend connection error:")

        print(exc)

        return False


    print()
    print("Resend status:")
    print(response.status_code)

    print()
    print("Resend response:")
    print(response.text)


    if response.status_code in (200, 201):

        print()
        print("=" * 70)
        print("✅ EMAIL SENT SUCCESSFULLY")
        print("=" * 70)

        return True


    print()
    print("=" * 70)
    print("❌ EMAIL FAILED")
    print("=" * 70)

    return False


# ============================================================
# MAIN PIPELINE
# ============================================================

def main() -> int:

    start_time = datetime.now()


    print()
    print("=" * 70)
    print("STARTING MAIN PIPELINE")
    print("=" * 70)


    # ========================================================
    # STEP 1 - YOUTUBE ANALYSIS
    # ========================================================

    youtube_candidates = [

        SRC_DIR / "youtube_agent.py",

        PROJECT_ROOT / "youtube_agent.py",

        SRC_DIR / "youtube_trend_analysis.py",

        PROJECT_ROOT / "youtube_trend_analysis.py",

    ]


    youtube_script = None


    for candidate in youtube_candidates:

        if candidate.exists():

            youtube_script = candidate

            break


    if youtube_script:

        success = run_script(
            youtube_script,
            "STEP 1 - FETCHING YOUTUBE TREND DATA",
            required=True
        )


        if not success:

            return 1

    else:

        print()
        print("⚠️ WARNING:")
        print("No YouTube analysis script was found.")

        print()
        print("Checked:")

        for candidate in youtube_candidates:

            print(f"  {candidate}")

        print()
        print(
            "Continuing to the idea/PDF generation stage..."
        )


    # ========================================================
    # STEP 2 - IDEA GENERATOR
    # ========================================================

    idea_candidates = [

        SRC_DIR / "idea_generator.py",

        PROJECT_ROOT / "idea_generator.py",

    ]


    idea_script = None


    for candidate in idea_candidates:

        if candidate.exists():

            idea_script = candidate

            break


    if idea_script:

        success = run_script(
            idea_script,
            "STEP 2 - GENERATING CONTENT IDEAS",
            required=False
        )


        if not success:

            print()
            print(
                "⚠️ Idea generator failed."
            )

            print(
                "Continuing to PDF generation..."
            )


    else:

        print()
        print(
            "⚠️ idea_generator.py not found."
        )

        print(
            "Continuing..."
        )


    # ========================================================
    # STEP 3 - PDF GENERATION
    # ========================================================

    pdf_candidates = [

        SRC_DIR / "PDF_Generator.py",

        PROJECT_ROOT / "PDF_Generator.py",

        SRC_DIR / "pdf_generator.py",

        PROJECT_ROOT / "pdf_generator.py",

    ]


    pdf_generator = None


    for candidate in pdf_candidates:

        if candidate.exists():

            pdf_generator = candidate

            break


    if pdf_generator is None:

        print()
        print("❌ PDF generator not found.")

        print()
        print("Checked:")

        for candidate in pdf_candidates:

            print(f"  {candidate}")

        return 1


    success = run_script(
        pdf_generator,
        "STEP 3 - CREATING PROFESSIONAL PDF REPORT",
        required=True
    )


    if not success:

        print()
        print("❌ PDF generation failed.")

        return 1


    # ========================================================
    # FIND PDF
    # ========================================================

    print()
    print("=" * 70)
    print("SEARCHING FOR GENERATED PDF")
    print("=" * 70)


    pdfs = find_pdfs()


    if not pdfs:

        print()
        print("❌ NO PDF FOUND.")

        print()
        print("Searched:")

        print(f"  {PROJECT_ROOT}")
        print(f"  {PROJECT_ROOT / 'reports'}")
        print(f"  {PROJECT_ROOT / 'output'}")
        print(f"  {PROJECT_ROOT / 'generated'}")
        print(f"  {PROJECT_ROOT / 'pdf'}")
        print(f"  {SRC_DIR}")

        return 1


    print()
    print(
        f"✓ Found {len(pdfs)} PDF file(s)"
    )


    for pdf in pdfs:

        print(
            f"  ✓ {pdf}"
        )


    newest_pdf = pdfs[0]


    print()
    print("Latest report:")
    print(newest_pdf)


    # ========================================================
    # SEND EMAIL
    # ========================================================

    email_success = send_report_email(
        newest_pdf
    )


    if not email_success:

        print()
        print(
            "❌ MAIN TRIGGER FAILED "
            "BECAUSE EMAIL WAS NOT SENT."
        )

        return 1


    # ========================================================
    # COMPLETE
    # ========================================================

    end_time = datetime.now()

    duration = end_time - start_time


    print()
    print("=" * 70)
    print("YOUTUBE TREND ANALYSIS COMPLETED")
    print("=" * 70)

    print()
    print(f"Started : {start_time}")
    print(f"Finished: {end_time}")
    print(f"Duration: {duration}")

    print()
    print("✅ MAIN TRIGGER FINISHED SUCCESSFULLY")


    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        exit_code = main()


    except KeyboardInterrupt:

        print()
        print("⚠️ Process interrupted by user.")

        exit_code = 130


    except Exception as exc:

        print()
        print("=" * 70)
        print("❌ FATAL ERROR")
        print("=" * 70)

        print()
        print(
            f"{type(exc).__name__}: {exc}"
        )

        import traceback

        traceback.print_exc()

        exit_code = 1


    sys.exit(exit_code)
