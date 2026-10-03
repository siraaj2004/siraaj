import os
import sys
import traceback
from pathlib import Path
from datetime import datetime


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
SUMMARIES_DIR = BASE_DIR / "summaries"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# ENVIRONMENT
# ============================================================

try:
    from dotenv import load_dotenv

    env_file = BASE_DIR / ".env"

    if env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()

except ImportError:
    pass


# ============================================================
# HELPERS
# ============================================================

def print_header():
    print()
    print("=" * 50)
    print("STARTING YOUTUBE TREND INTELLIGENCE")
    print("=" * 50)
    print()


def check_environment():
    print("Checking environment variables...")
    print()

    required = {
        "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GMAIL_USER": os.getenv("GMAIL_USER"),
        "GMAIL_TO": os.getenv("GMAIL_TO"),
        "GMAIL_APP_PASSWORD": os.getenv("GMAIL_APP_PASSWORD"),
    }

    missing = []

    for name, value in required.items():
        if value:
            print(f"✓ {name} found")
        else:
            print(f"✗ {name} is missing")
            missing.append(name)

    print()

    if missing:
        print("=" * 50)
        print("ERROR: REQUIRED ENVIRONMENT VARIABLES ARE MISSING")
        print("=" * 50)

        for item in missing:
            print(f"  - {item}")

        print()
        print("GitHub Actions must provide these values through")
        print("Repository Secrets.")
        print()

        return False

    return True


# ============================================================
# RUN MODULE
# ============================================================

def run_module(module_name):
    """
    Run another Python module located inside src/.
    """

    module_path = SRC_DIR / module_name

    if not module_path.exists():
        print()
        print(f"ERROR: Module not found:")
        print(f"  {module_path}")
        print()

        return False

    print()
    print("=" * 70)
    print(f"RUNNING: {module_name}")
    print("=" * 70)
    print()

    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, str(module_path)],
            cwd=str(BASE_DIR),
            env=os.environ.copy(),
            check=False,
        )

        if result.returncode != 0:
            print()
            print(f"ERROR: {module_name} failed.")
            print(f"Exit code: {result.returncode}")
            print()

            return False

        print()
        print(f"✓ {module_name} completed successfully")
        print()

        return True

    except Exception as exc:
        print()
        print(f"ERROR while running {module_name}:")
        print(str(exc))
        print()

        traceback.print_exc()

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    print_header()

    print(f"Project root : {BASE_DIR}")
    print(f"Source folder: {SRC_DIR}")
    print(f"Data folder  : {DATA_DIR}")
    print(f"Reports      : {REPORTS_DIR}")
    print(f"Summaries    : {SUMMARIES_DIR}")
    print()

    # --------------------------------------------------------
    # Check required secrets
    # --------------------------------------------------------

    if not check_environment():
        return 1

    # --------------------------------------------------------
    # Step 1 - YouTube trend collection
    # --------------------------------------------------------

    youtube_success = run_module("youtube_agent.py")

    if not youtube_success:
        print()
        print("=" * 50)
        print("YOUTUBE TREND COLLECTION FAILED")
        print("=" * 50)
        return 1

    # --------------------------------------------------------
    # Step 2 - AI idea generation
    # --------------------------------------------------------

    idea_success = run_module("idea_generator.py")

    if not idea_success:
        print()
        print("=" * 50)
        print("AI IDEA GENERATION FAILED")
        print("=" * 50)
        return 1

    # --------------------------------------------------------
    # Step 3 - Optional email module
    # --------------------------------------------------------

    email_module = SRC_DIR / "email_report.py"

    if email_module.exists():

        print()
        print("=" * 70)
        print("EMAIL MODULE FOUND")
        print("=" * 70)
        print()

        email_success = run_module("email_report.py")

        if not email_success:
            print()
            print("WARNING: Email sending failed.")
            print("The trend and AI report were generated successfully.")
            print()

            # Do not fail the entire workflow only because email failed.
        else:
            print("✓ Email sent successfully")

    else:
        print()
        print("No email_report.py found.")
        print("Skipping email step.")
        print()

    # --------------------------------------------------------
    # Finished
    # --------------------------------------------------------

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print()
    print("=" * 70)
    print("YOUTUBE TREND INTELLIGENCE COMPLETED")
    print("=" * 70)
    print()
    print(f"Completed at: {now}")
    print()
    print("Generated files can be found in:")
    print(f"  {DATA_DIR}")
    print(f"  {REPORTS_DIR}")
    print(f"  {SUMMARIES_DIR}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
