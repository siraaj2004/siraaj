```python
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
SUMMARIES_DIR = PROJECT_ROOT / "summaries"

ENV_FILE = PROJECT_ROOT / ".env"


# ============================================================
# CREATE REQUIRED FOLDERS
# ============================================================

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD .ENV
# ============================================================

if load_dotenv:
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
        print(f"✓ Loaded environment file: {ENV_FILE}")
    else:
        print("⚠ .env file not found.")
        print("Using environment variables from the system/GitHub Actions.")


# ============================================================
# HELPERS
# ============================================================

def get_env(name):
    """
    Get environment variable safely.
    """
    value = os.getenv(name)

    if value:
        return value.strip()

    return None


def check_environment():
    """
    Check all required environment variables.
    """

    print()
    print("=" * 70)
    print("CHECKING ENVIRONMENT VARIABLES")
    print("=" * 70)

    required = {
        "YOUTUBE_API_KEY": get_env("YOUTUBE_API_KEY"),
        "OPENROUTER_API_KEY": get_env("OPENROUTER_API_KEY"),
        "GMAIL_USER": get_env("GMAIL_USER"),
        "GMAIL_TO": get_env("GMAIL_TO"),
        "GMAIL_APP_PASSWORD": get_env("GMAIL_APP_PASSWORD"),
    }

    missing = []

    for name, value in required.items():

        if value:
            print(f"✓ {name} found")
        else:
            print(f"⚠ {name} not found")
            missing.append(name)

    print()

    # YouTube API is mandatory
    if not required["YOUTUBE_API_KEY"]:
        print("ERROR: YOUTUBE_API_KEY is missing.")
        return False

    # OpenRouter is mandatory because the project generates AI ideas
    if not required["OPENROUTER_API_KEY"]:
        print()
        print("=" * 70)
        print("ERROR: OPENROUTER_API_KEY IS MISSING")
        print("=" * 70)
        print()
        print("For GitHub Actions:")
        print("GitHub Repository")
        print("→ Settings")
        print("→ Secrets and variables")
        print("→ Actions")
        print("→ New repository secret")
        print()
        print("Name:")
        print("OPENROUTER_API_KEY")
        print()
        print("Then paste your OpenRouter API key as the value.")
        print()
        return False

    # Gmail variables are needed for email delivery
    if not required["GMAIL_USER"]:
        print("ERROR: GMAIL_USER is missing.")
        return False

    if not required["GMAIL_TO"]:
        print("ERROR: GMAIL_TO is missing.")
        return False

    if not required["GMAIL_APP_PASSWORD"]:
        print("ERROR: GMAIL_APP_PASSWORD is missing.")
        return False

    print("✓ All required environment variables are available.")
    print()

    return True


# ============================================================
# RUN PYTHON SCRIPT
# ============================================================

def run_script(script_name):
    """
    Run another Python script from src/.
    """

    script_path = SRC_DIR / script_name

    if not script_path.exists():
        print()
        print(f"ERROR: {script_name} was not found.")
        print(f"Expected location: {script_path}")
        return False

    print()
    print("=" * 70)
    print(f"RUNNING: {script_path}")
    print("=" * 70)
    print()

    try:

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(PROJECT_ROOT),
            env=os.environ.copy(),
            check=False
        )

        if result.returncode != 0:

            print()
            print(f"ERROR: {script_name} failed.")
            print(f"Exit code: {result.returncode}")

            return False

        print()
        print(f"✓ {script_name} completed successfully.")

        return True

    except Exception as e:

        print()
        print(f"ERROR while running {script_name}:")
        print(str(e))

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("YOUTUBE TREND INTELLIGENCE + IDEA GENERATOR")
    print("=" * 70)

    print(f"Project root : {PROJECT_ROOT}")
    print(f"Output folder: {SUMMARIES_DIR}")
    print(
        "Generated    : "
        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    print()

    # --------------------------------------------------------
    # ENVIRONMENT CHECK
    # --------------------------------------------------------

    if not check_environment():

        print()
        print("=" * 70)
        print("PROGRAM STOPPED")
        print("=" * 70)

        sys.exit(1)

    # --------------------------------------------------------
    # STEP 1
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("STEP 1 - FETCHING YOUTUBE TREND DATA")
    print("=" * 70)

    if not run_script("youtube_agent.py"):
        sys.exit(1)

    # --------------------------------------------------------
    # STEP 2
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("STEP 2 - GENERATING AI TREND SUMMARY")
    print("=" * 70)

    # Change this filename if your project uses another AI script.
    ai_script = "ai_agent.py"

    if (SRC_DIR / ai_script).exists():

        if not run_script(ai_script):
            sys.exit(1)

    else:
        print()
        print(f"⚠ {ai_script} not found.")
        print("Skipping separate AI step.")
        print("AI processing may already be inside youtube_agent.py.")

    # --------------------------------------------------------
    # STEP 3 - EMAIL
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("STEP 3 - SENDING EMAIL")
    print("=" * 70)

    email_scripts = [
        "email_agent.py",
        "send_email.py",
        "gmail_sender.py"
    ]

    email_script_found = False

    for script in email_scripts:

        if (SRC_DIR / script).exists():

            email_script_found = True

            if not run_script(script):
                sys.exit(1)

            break

    if not email_script_found:

        print()
        print("⚠ No separate email script found.")
        print("Skipping email step.")

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("YOUTUBE TREND INTELLIGENCE GENERATOR COMPLETED")
    print("=" * 70)
    print()
    print(f"Reports   : {REPORTS_DIR}")
    print(f"Summaries : {SUMMARIES_DIR}")
    print()
    print("✓ Finished successfully.")


if __name__ == "__main__":
    main()
```
