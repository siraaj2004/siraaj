"""
YouTube Trend Intelligence Generator
-------------------------------------

MAIN TRIGGER

GitHub Actions should run:

    python src/app.py

This file:
1. Finds the project root
2. Loads .env from the project root
3. Validates required environment variables
4. Runs the YouTube trend analysis
5. Runs the idea generator if present
6. Runs the PDF generator if present
7. Finds the generated PDF
8. Exits with code 0 on success
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


# ============================================================
# PATH CONFIGURATION
# ============================================================

# app.py is inside:
# /repository/src/app.py
#
# Therefore:
# parent      = /repository/src
# parent.parent = /repository

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

os.chdir(PROJECT_ROOT)

print("=" * 70)
print("       YOUTUBE TREND INTELLIGENCE GENERATOR")
print("=" * 70)

print(f"\nProject root:")
print(PROJECT_ROOT)

print(f"\nSource folder:")
print(SRC_DIR)


# ============================================================
# LOAD .ENV
# ============================================================

try:
    from dotenv import load_dotenv
except ImportError:
    print("\nERROR: python-dotenv is not installed.")
    print("Install it with:")
    print("pip install python-dotenv")
    sys.exit(1)


ENV_FILE = PROJECT_ROOT / ".env"

print(f"\nLooking for .env:")
print(ENV_FILE)

if not ENV_FILE.exists():
    print("\nERROR: .env file was not found.")
    print(f"Expected location:")
    print(ENV_FILE)
    print("\nGitHub Actions should create .env in the repository root.")
    sys.exit(1)

load_dotenv(ENV_FILE)

print("\n.env loaded successfully.")


# ============================================================
# ENVIRONMENT VALIDATION
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

print("\nChecking environment variables...")

if not YOUTUBE_API_KEY:
    print("ERROR: YOUTUBE_API_KEY is missing.")
    sys.exit(1)

print("✓ YOUTUBE_API_KEY found")

if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY is missing.")
    sys.exit(1)

print("✓ GEMINI_API_KEY found")


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def run_python_script(
    script: Path,
    description: str,
    required: bool = True,
) -> bool:
    """
    Run another Python script safely.

    Returns:
        True  -> script succeeded
        False -> script failed
    """

    if not script.exists():
        message = f"{script} not found."

        if required:
            print(f"\nERROR: {message}")
            return False

        print(f"\nWARNING: {message}")
        print("Skipping...")
        return True

    print("\n" + "=" * 70)
    print(description)
    print("=" * 70)

    print(f"\nRunning:")
    print(script)

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(PROJECT_ROOT),
            env=os.environ.copy(),
            check=False,
        )

    except Exception as exc:
        print(f"\nERROR while running {script.name}:")
        print(exc)
        return False

    if result.returncode != 0:
        print(
            f"\nERROR: {script.name} failed "
            f"with exit code {result.returncode}"
        )
        return False

    print(f"\n✓ {description} completed successfully.")
    return True


def find_generated_pdfs() -> list[Path]:
    """
    Search common locations for generated PDF reports.
    """

    search_locations = [
        PROJECT_ROOT,
        PROJECT_ROOT / "reports",
        PROJECT_ROOT / "output",
        PROJECT_ROOT / "generated",
        PROJECT_ROOT / "pdf",
        SRC_DIR,
    ]

    pdfs: list[Path] = []

    for location in search_locations:
        if not location.exists():
            continue

        try:
            for pdf in location.glob("*.pdf"):
                if pdf.is_file() and pdf not in pdfs:
                    pdfs.append(pdf)
        except Exception:
            continue

    return sorted(
        pdfs,
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def print_project_structure() -> None:
    """
    Print important files for GitHub Actions debugging.
    """

    print("\n" + "=" * 70)
    print("PROJECT STRUCTURE")
    print("=" * 70)

    important_files = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "requirements.txt",
        SRC_DIR / "app.py",
        SRC_DIR / "idea_generator.py",
        SRC_DIR / "youtube_agent.py",
        PROJECT_ROOT / "PDF_Generator.py",
        PROJECT_ROOT / "config.py",
    ]

    for file in important_files:
        status = "FOUND" if file.exists() else "NOT FOUND"
        print(f"{status:12} {file}")


# ============================================================
# DEBUG INFORMATION
# ============================================================

print_project_structure()


# ============================================================
# MAIN PIPELINE
# ============================================================

def main() -> int:

    start_time = datetime.now()

    print("\n" + "=" * 70)
    print("STARTING MAIN PIPELINE")
    print("=" * 70)

    print(f"\nStarted:")
    print(start_time.strftime("%Y-%m-%d %H:%M:%S"))

    # --------------------------------------------------------
    # STEP 1
    # YouTube trend analysis
    # --------------------------------------------------------

    youtube_agent = SRC_DIR / "youtube_agent.py"

    if youtube_agent.exists():

        success = run_python_script(
            youtube_agent,
            "STEP 1/3 - FETCHING YOUTUBE TREND DATA",
            required=True,
        )

        if not success:
            return 1

    else:
        print(
            "\nWARNING: youtube_agent.py was not found."
        )
        print(
            "The main trigger cannot automatically fetch "
            "YouTube data without it."
        )

    # --------------------------------------------------------
    # STEP 2
    # Idea generation
    # --------------------------------------------------------

    idea_generator = SRC_DIR / "idea_generator.py"

    if idea_generator.exists():

        success = run_python_script(
            idea_generator,
            "STEP 2/3 - GENERATING CONTENT IDEAS",
            required=False,
        )

        if not success:
            print(
                "\nWARNING: Idea generation failed."
            )
            print(
                "Continuing to PDF generation..."
            )

    else:
        print(
            "\nWARNING: idea_generator.py not found."
        )

    # --------------------------------------------------------
    # STEP 3
    # PDF generation
    # --------------------------------------------------------

    pdf_generator_candidates = [
        PROJECT_ROOT / "PDF_Generator.py",
        SRC_DIR / "PDF_Generator.py",
        SRC_DIR / "pdf_generator.py",
    ]

    pdf_generator = None

    for candidate in pdf_generator_candidates:
        if candidate.exists():
            pdf_generator = candidate
            break

    if pdf_generator:

        success = run_python_script(
            pdf_generator,
            "STEP 3/3 - CREATING PROFESSIONAL PDF REPORT",
            required=False,
        )

        if not success:
            print(
                "\nWARNING: PDF generation failed."
            )

    else:
        print(
            "\nWARNING: PDF generator was not found."
        )


    # ========================================================
    # FIND GENERATED PDF
    # ========================================================

    print("\n" + "=" * 70)
    print("CHECKING GENERATED REPORTS")
    print("=" * 70)

    pdfs = find_generated_pdfs()

    if pdfs:

        print(f"\nFound {len(pdfs)} PDF file(s):")

        for pdf in pdfs:
            print(f"  ✓ {pdf}")

        newest_pdf = pdfs[0]

        print("\nLatest report:")
        print(newest_pdf)

    else:

        print("\nWARNING: No PDF report was found.")

        print("\nSearched:")
        print(f"  {PROJECT_ROOT}")
        print(f"  {PROJECT_ROOT / 'reports'}")
        print(f"  {PROJECT_ROOT / 'output'}")
        print(f"  {PROJECT_ROOT / 'generated'}")
        print(f"  {PROJECT_ROOT / 'pdf'}")

        # Do not automatically fail here because the
        # analysis may have completed without PDF generation.

    # ========================================================
    # FINISHED
    # ========================================================

    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 70)
    print("YOUTUBE TREND ANALYSIS COMPLETED")
    print("=" * 70)

    print(f"\nStarted : {start_time}")
    print(f"Finished: {end_time}")
    print(f"Duration: {duration}")

    print("\n✓ MAIN TRIGGER FINISHED SUCCESSFULLY")

    return 0


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        exit_code = main()

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        exit_code = 130

    except Exception as exc:
        print("\n" + "=" * 70)
        print("FATAL ERROR")
        print("=" * 70)

        print(f"\n{type(exc).__name__}: {exc}")

        import traceback
        traceback.print_exc()

        exit_code = 1

    sys.exit(exit_code)
