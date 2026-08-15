import os
import sys
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv


# ============================================================
# PROJECT PATHS
# ============================================================

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TREND_FILE = DATA_DIR / "youtube_trends.json"
IDEA_FILE = DATA_DIR / "content_ideas.json"
PDF_FILE = REPORTS_DIR / "youtube_trend_report.pdf"


# ============================================================
# LOAD .ENV
# ============================================================

ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"✓ .env loaded: {ENV_FILE}")

else:
    print("⚠ Project .env not found.")
    print("Checking src/.env...")

    SRC_ENV_FILE = SRC_DIR / ".env"

    if SRC_ENV_FILE.exists():
        load_dotenv(SRC_ENV_FILE)
        print(f"✓ .env loaded: {SRC_ENV_FILE}")

    else:
        print("⚠ No .env file found.")
        print("Using system environment variables.")


# ============================================================
# FIND SCRIPT
# ============================================================

def find_script(filename):
    """
    Find a Python script in common project locations.
    """

    possible_paths = [
        SRC_DIR / filename,
        PROJECT_ROOT / filename,
    ]

    for path in possible_paths:

        if path.exists() and path.is_file():
            return path

    return None


# ============================================================
# RUN PYTHON SCRIPT
# ============================================================

def run_script(script_path, extra_env=None):

    print()
    print("=" * 80)
    print(f"RUNNING: {script_path}")
    print("=" * 80)

    environment = os.environ.copy()

    if extra_env:
        environment.update(extra_env)

    try:

        result = subprocess.run(
            [
                sys.executable,
                str(script_path)
            ],
            cwd=str(PROJECT_ROOT),
            env=environment,
            capture_output=True,
            text=True
        )

    except Exception as e:

        print()
        print(f"❌ Could not start {script_path.name}")
        print(f"Error: {e}")

        return False

    # Print normal output
    if result.stdout:
        print(result.stdout)

    # Print errors
    if result.stderr:
        print()
        print("ERROR OUTPUT:")
        print(result.stderr)

    if result.returncode != 0:

        print()
        print(
            f"❌ {script_path.name} failed "
            f"with exit code {result.returncode}"
        )

        return False

    print()
    print(
        f"✓ {script_path.name} completed successfully."
    )

    return True


# ============================================================
# CHECK ENVIRONMENT
# ============================================================

def check_environment():

    print()
    print("=" * 80)
    print("CHECKING ENVIRONMENT VARIABLES")
    print("=" * 80)

    required = {
        "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY"),
    }

    optional = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
        "FROM_EMAIL": os.getenv("FROM_EMAIL"),
        "RECIPIENT_EMAIL": os.getenv("RECIPIENT_EMAIL"),
    }

    failed = False

    for name, value in required.items():

        if value:
            print(f"✓ {name} found")

        else:
            print(f"❌ {name} NOT found")
            failed = True

    for name, value in optional.items():

        if value:
            print(f"✓ {name} found")

        else:
            print(f"⚠ {name} not found")

    if failed:

        print()
        print("❌ Required environment variables are missing.")
        return False

    return True


# ============================================================
# FIND GENERATED PDF
# ============================================================

def find_pdf():

    # First check the expected location
    if PDF_FILE.exists():

        if PDF_FILE.stat().st_size > 0:
            return PDF_FILE

    # Search other common folders
    search_directories = [
        PROJECT_ROOT,
        REPORTS_DIR,
        PROJECT_ROOT / "output",
        PROJECT_ROOT / "generated",
        PROJECT_ROOT / "pdf",
        SRC_DIR,
    ]

    found = []

    for directory in search_directories:

        if not directory.exists():
            continue

        try:

            for pdf in directory.rglob("*.pdf"):

                if pdf.is_file() and pdf.stat().st_size > 0:

                    found.append(pdf)

        except Exception:
            continue

    if not found:
        return None

    # Newest PDF
    found.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    return found[0]


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("YOUTUBE TREND INTELLIGENCE GENERATOR")
    print("=" * 80)

    print()
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Source folder: {SRC_DIR}")
    print(f"Data folder  : {DATA_DIR}")
    print(f"Reports folder: {REPORTS_DIR}")

    # ========================================================
    # ENVIRONMENT
    # ========================================================

    if not check_environment():
        sys.exit(1)

    # ========================================================
    # STEP 1
    # YOUTUBE TREND COLLECTION
    # ========================================================

    print()
    print("=" * 80)
    print("STEP 1 - FETCHING YOUTUBE TREND DATA")
    print("=" * 80)

    youtube_agent = find_script(
        "youtube_agent.py"
    )

    if youtube_agent is None:

        print()
        print("❌ youtube_agent.py NOT FOUND")
        print()
        print("I checked:")
        print(f"  {SRC_DIR / 'youtube_agent.py'}")
        print(f"  {PROJECT_ROOT / 'youtube_agent.py'}")
        print()
        print("Put youtube_agent.py inside src/")
        print("or inside the project root.")

        sys.exit(1)

    print(
        f"✓ Found youtube_agent.py:"
        f"\n  {youtube_agent}"
    )

    youtube_success = run_script(
        youtube_agent
    )

    if not youtube_success:

        print()
        print("❌ STEP 1 FAILED.")
        print("Pipeline stopped.")

        sys.exit(1)

    # ========================================================
    # CHECK TREND JSON
    # ========================================================

    print()
    print("=" * 80)
    print("CHECKING TREND DATA")
    print("=" * 80)

    # Some youtube_agent versions may create the file
    # in a different location.

    possible_trend_files = [
        TREND_FILE,
        PROJECT_ROOT / "youtube_trends.json",
        SRC_DIR / "youtube_trends.json",
        DATA_DIR / "trends.json",
    ]

    actual_trend_file = None

    for file in possible_trend_files:

        if file.exists() and file.stat().st_size > 0:

            actual_trend_file = file
            break

    if actual_trend_file is None:

        print("⚠ youtube_trends.json was not found.")
        print()
        print("The youtube_agent.py output may be text-only.")

        # Don't stop immediately because some versions of
        # youtube_agent.py only print the trends.

    else:

        print(
            f"✓ Trend data found:\n"
            f"  {actual_trend_file}"
        )

        # Copy to standard location if necessary
        if actual_trend_file != TREND_FILE:

            import shutil

            shutil.copy2(
                actual_trend_file,
                TREND_FILE
            )

            print(
                f"✓ Copied trend data to:\n"
                f"  {TREND_FILE}"
            )

    # ========================================================
    # STEP 2
    # IDEA GENERATOR
    # ========================================================

    print()
    print("=" * 80)
    print("STEP 2 - GENERATING CONTENT IDEAS")
    print("=" * 80)

    idea_generator = find_script(
        "idea_generator.py"
    )

    if idea_generator is None:

        print()
        print("❌ idea_generator.py NOT FOUND")
        print()
        print(
            f"Expected:\n"
            f"  {SRC_DIR / 'idea_generator.py'}"
        )

        sys.exit(1)

    # If trend JSON doesn't exist, idea generator cannot work.
    if not TREND_FILE.exists():

        print()
        print("❌ Trend JSON file does not exist:")
        print(TREND_FILE)
        print()
        print(
            "Your youtube_agent.py needs to save the "
            "trend data as youtube_trends.json."
        )

        sys.exit(1)

    idea_success = run_script(
        idea_generator,
        {
            "TREND_DATA_FILE": str(TREND_FILE),
            "IDEA_OUTPUT_FILE": str(IDEA_FILE),
        }
    )

    if not idea_success:

        print()
        print("❌ STEP 2 FAILED.")
        print("Pipeline stopped.")

        sys.exit(1)

    # ========================================================
    # CHECK IDEA FILE
    # ========================================================

    if not IDEA_FILE.exists():

        print()
        print("❌ idea_generator.py completed but")
        print("did not create:")
        print(IDEA_FILE)

        sys.exit(1)

    print(
        f"✓ Content ideas file found:\n"
        f"  {IDEA_FILE}"
    )

    # ========================================================
    # STEP 3
    # PDF GENERATION
    # ========================================================

    print()
    print("=" * 80)
    print("STEP 3 - CREATING PROFESSIONAL PDF REPORT")
    print("=" * 80)

    pdf_generator = PROJECT_ROOT / "PDF_Generator.py"

    if not pdf_generator.exists():

        pdf_generator = SRC_DIR / "PDF_Generator.py"

    if not pdf_generator.exists():

        print()
        print("❌ PDF_Generator.py NOT FOUND")
        print()
        print("Expected either:")
        print(
            f"  {PROJECT_ROOT / 'PDF_Generator.py'}"
        )
        print(
            f"  {SRC_DIR / 'PDF_Generator.py'}"
        )

        sys.exit(1)

    # Delete old PDF
    if PDF_FILE.exists():

        try:
            PDF_FILE.unlink()
            print("✓ Removed old PDF")

        except Exception as e:

            print(
                f"⚠ Could not remove old PDF: {e}"
            )

    pdf_success = run_script(
        pdf_generator,
        {
            "TREND_DATA_FILE": str(TREND_FILE),
            "IDEA_DATA_FILE": str(IDEA_FILE),
            "PDF_OUTPUT_FILE": str(PDF_FILE),
        }
    )

    if not pdf_success:

        print()
        print("❌ STEP 3 FAILED.")
        sys.exit(1)

    # ========================================================
    # FIND PDF
    # ========================================================

    print()
    print("=" * 80)
    print("SEARCHING FOR GENERATED PDF")
    print("=" * 80)

    generated_pdf = find_pdf()

    if generated_pdf is None:

        print()
        print("❌ NO PDF FOUND.")

        print()
        print("Expected:")
        print(
            f"  {PDF_FILE}"
        )

        print()
        print("Searched:")
        print(
            f"  {PROJECT_ROOT}"
        )
        print(
            f"  {REPORTS_DIR}"
        )
        print(
            f"  {PROJECT_ROOT / 'output'}"
        )
        print(
            f"  {PROJECT_ROOT / 'generated'}"
        )
        print(
            f"  {PROJECT_ROOT / 'pdf'}"
        )
        print(
            f"  {SRC_DIR}"
        )

        sys.exit(1)

    # ========================================================
    # STANDARDIZE PDF LOCATION
    # ========================================================

    if generated_pdf.resolve() != PDF_FILE.resolve():

        import shutil

        print()
        print(
            f"PDF found elsewhere:\n"
            f"  {generated_pdf}"
        )

        shutil.copy2(
            generated_pdf,
            PDF_FILE
        )

        generated_pdf = PDF_FILE

        print(
            f"✓ PDF copied to:\n"
            f"  {PDF_FILE}"
        )

    # ========================================================
    # PDF SUCCESS
    # ========================================================

    print()
    print("=" * 80)
    print("PDF GENERATED SUCCESSFULLY")
    print("=" * 80)

    print(
        f"✓ PDF: {generated_pdf}"
    )

    print(
        f"✓ Size: "
        f"{generated_pdf.stat().st_size:,} bytes"
    )

    # ========================================================
    # STEP 4
    # EMAIL
    # ========================================================

    sender = SRC_DIR / "sender.py"

    if not sender.exists():
        sender = PROJECT_ROOT / "sender.py"

    if sender.exists():

        print()
        print("=" * 80)
        print("STEP 4 - SENDING EMAIL")
        print("=" * 80)

        email_success = run_script(
            sender,
            {
                "PDF_FILE": str(generated_pdf),
                "REPORT_PDF": str(generated_pdf),
            }
        )

        if email_success:

            print()
            print("✓ EMAIL SENT SUCCESSFULLY")

        else:

            print()
            print(
                "⚠ EMAIL FAILED."
            )

            print(
                "The PDF was generated successfully, "
                "so the pipeline will not delete it."
            )

    else:

        print()
        print(
            "⚠ sender.py not found."
        )

        print(
            "Skipping email step."
        )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 80)
    print("🎉 PIPELINE COMPLETED")
    print("=" * 80)

    print()
    print("Files generated:")

    print(
        f"✓ Trends : {TREND_FILE}"
    )

    print(
        f"✓ Ideas  : {IDEA_FILE}"
    )

    print(
        f"✓ PDF    : {generated_pdf}"
    )

    print()
    print("=" * 80)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
