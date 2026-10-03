import os
import sys
import json
import glob
import subprocess
import smtplib
import ssl
from pathlib import Path
from datetime import datetime
from email.message import EmailMessage
from xml.sax.saxutils import escape


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
SUMMARIES_DIR = PROJECT_ROOT / "summaries"
REPORTS_DIR = PROJECT_ROOT / "reports"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def separator():
    print("\n" + "=" * 80)


def run_python_script(script_name):
    """
    Run another Python script from src/.
    """

    script_path = SRC_DIR / script_name

    separator()
    print(f"RUNNING: {script_path}")
    separator()

    if not script_path.exists():
        print(f"ERROR: Script not found:")
        print(script_path)
        sys.exit(1)

    result = subprocess.run(
        [
            sys.executable,
            str(script_path)
        ],
        cwd=str(PROJECT_ROOT),
        env=os.environ.copy()
    )

    if result.returncode != 0:
        print()
        print(f"ERROR: {script_name} failed.")
        print(f"Exit code: {result.returncode}")
        sys.exit(result.returncode)

    print()
    print(f"✓ {script_name} completed successfully.")


# ============================================================
# ENVIRONMENT
# ============================================================

def check_environment():

    separator()
    print("CHECKING ENVIRONMENT VARIABLES")
    separator()

    variables = [
        "YOUTUBE_API_KEY",
        "OPENROUTER_API_KEY",
        "GMAIL_USER",
        "GMAIL_TO",
        "GMAIL_APP_PASSWORD"
    ]

    for name in variables:

        value = os.getenv(name)

        if value:
            print(f"✓ {name} found")
        else:
            print(f"⚠ {name} not found")


# ============================================================
# FIND LATEST GENERATED IDEAS FILE
# ============================================================

def find_latest_ideas_json():

    separator()
    print("SEARCHING FOR GENERATED IDEA FILE")
    separator()

    patterns = [
        str(SUMMARIES_DIR / "youtube_ideas_*.json"),
        str(DATA_DIR / "youtube_ideas_*.json"),
        str(PROJECT_ROOT / "youtube_ideas_*.json")
    ]

    files = []

    for pattern in patterns:
        files.extend(glob.glob(pattern))

    # Remove duplicates
    files = list(set(files))

    if not files:

        print("❌ No generated YouTube ideas JSON file found.")

        print()
        print("Searched:")

        for pattern in patterns:
            print(pattern)

        return None

    # Newest file first
    files.sort(
        key=lambda file: os.path.getmtime(file),
        reverse=True
    )

    latest_file = Path(files[0])

    print("✓ Generated idea file found:")
    print(f"  {latest_file}")

    return latest_file


# ============================================================
# CREATE content_ideas.json
# ============================================================

def create_content_ideas():

    separator()
    print("CREATING CONTENT IDEAS FILE")
    separator()

    source_file = find_latest_ideas_json()

    if source_file is None:
        print("❌ Cannot create data/content_ideas.json")
        sys.exit(1)

    target_file = DATA_DIR / "content_ideas.json"

    try:

        # Validate JSON first
        with open(
            source_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        # Save standard application file
        with open(
            target_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )

        print("✓ Content ideas created successfully.")
        print()
        print(f"Source:")
        print(source_file)
        print()
        print(f"Target:")
        print(target_file)

        return target_file

    except json.JSONDecodeError as error:

        print("❌ Generated JSON is invalid.")
        print(error)

        sys.exit(1)

    except Exception as error:

        print("❌ Failed to create content_ideas.json")
        print(error)

        sys.exit(1)


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf():

    separator()
    print("CREATING PDF REPORT")
    separator()

    input_file = DATA_DIR / "content_ideas.json"

    if not input_file.exists():

        print("❌ content_ideas.json does not exist.")
        return None

    try:

        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer
        )
        from reportlab.lib.styles import (
            getSampleStyleSheet,
            ParagraphStyle
        )
        from reportlab.lib.enums import TA_CENTER

    except ImportError:

        print("❌ reportlab is not installed.")
        print("Install it with:")
        print("pip install reportlab")

        return None

    try:

        with open(
            input_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except Exception as error:

        print("❌ Could not read JSON:")
        print(error)

        return None

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    pdf_file = (
        REPORTS_DIR /
        f"youtube_trend_report_{timestamp}.pdf"
    )

    # --------------------------------------------------------
    # PDF styles
    # --------------------------------------------------------

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        spaceAfter=5
    )

    # --------------------------------------------------------
    # Document
    # --------------------------------------------------------

    document = SimpleDocTemplate(
        str(pdf_file),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    story = []

    story.append(
        Paragraph(
            "YouTube Trend Intelligence Report",
            title_style
        )
    )

    story.append(
        Paragraph(
            "Generated: "
            + datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            body_style
        )
    )

    story.append(Spacer(1, 15))

    # --------------------------------------------------------
    # Convert JSON to readable PDF
    # --------------------------------------------------------

    if isinstance(data, dict):

        for key, value in data.items():

            story.append(
                Paragraph(
                    escape(str(key)),
                    heading_style
                )
            )

            if isinstance(value, list):

                for index, item in enumerate(value, 1):

                    story.append(
                        Paragraph(
                            f"<b>Item {index}</b>",
                            body_style
                        )
                    )

                    if isinstance(item, dict):

                        for item_key, item_value in item.items():

                            text = (
                                f"<b>{escape(str(item_key))}:</b> "
                                f"{escape(str(item_value))}"
                            )

                            story.append(
                                Paragraph(
                                    text,
                                    body_style
                                )
                            )

                    else:

                        story.append(
                            Paragraph(
                                escape(str(item)),
                                body_style
                            )
                        )

                    story.append(
                        Spacer(1, 8)
                    )

            elif isinstance(value, dict):

                for item_key, item_value in value.items():

                    text = (
                        f"<b>{escape(str(item_key))}:</b> "
                        f"{escape(str(item_value))}"
                    )

                    story.append(
                        Paragraph(
                            text,
                            body_style
                        )
                    )

            else:

                story.append(
                    Paragraph(
                        escape(str(value)),
                        body_style
                    )
                )

    elif isinstance(data, list):

        for index, item in enumerate(data, 1):

            story.append(
                Paragraph(
                    f"Idea {index}",
                    heading_style
                )
            )

            if isinstance(item, dict):

                for key, value in item.items():

                    text = (
                        f"<b>{escape(str(key))}:</b> "
                        f"{escape(str(value))}"
                    )

                    story.append(
                        Paragraph(
                            text,
                            body_style
                        )
                    )

            else:

                story.append(
                    Paragraph(
                        escape(str(item)),
                        body_style
                    )
                )

    else:

        story.append(
            Paragraph(
                escape(str(data)),
                body_style
            )
        )

    # --------------------------------------------------------
    # Build PDF
    # --------------------------------------------------------

    document.build(story)

    if not pdf_file.exists():

        print("❌ PDF was not created.")
        return None

    print()
    print("✓ PDF CREATED SUCCESSFULLY")
    print(f"  {pdf_file}")

    return pdf_file


# ============================================================
# SEND EMAIL USING GMAIL SMTP
# ============================================================

def send_email(pdf_file):

    separator()
    print("SENDING EMAIL")
    separator()

    gmail_user = os.getenv("GMAIL_USER")
    gmail_to = os.getenv("GMAIL_TO")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    # --------------------------------------------------------
    # Check credentials
    # --------------------------------------------------------

    if not gmail_user:

        print("❌ GMAIL_USER is missing.")
        return False

    if not gmail_to:

        print("❌ GMAIL_TO is missing.")
        return False

    if not gmail_password:

        print("❌ GMAIL_APP_PASSWORD is missing.")
        return False

    # --------------------------------------------------------
    # Check PDF
    # --------------------------------------------------------

    if pdf_file is None:

        print("❌ PDF file is missing.")
        return False

    pdf_file = Path(pdf_file)

    if not pdf_file.exists():

        print("❌ PDF does not exist:")
        print(pdf_file)

        return False

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    try:

        message = EmailMessage()

        message["From"] = gmail_user
        message["To"] = gmail_to

        message["Subject"] = (
            "YouTube Trend Analysis Report - "
            + datetime.now().strftime(
                "%Y-%m-%d %H:%M"
            )
        )

        message.set_content(
            f"""
Hello,

Your YouTube Trend Intelligence report has been generated successfully.

Generated:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

The PDF report is attached.

Regards,
YouTube Trend Intelligence Generator
"""
        )

        # ----------------------------------------------------
        # Attach PDF
        # ----------------------------------------------------

        with open(
            pdf_file,
            "rb"
        ) as file:

            pdf_data = file.read()

        message.add_attachment(
            pdf_data,
            maintype="application",
            subtype="pdf",
            filename=pdf_file.name
        )

        # ----------------------------------------------------
        # Gmail SMTP
        # ----------------------------------------------------

        ssl_context = ssl.create_default_context()

        print("Connecting to Gmail...")
        print("SMTP server: smtp.gmail.com")
        print("Port: 587")

        with smtplib.SMTP(
            "smtp.gmail.com",
            587,
            timeout=60
        ) as server:

            server.ehlo()

            server.starttls(
                context=ssl_context
            )

            server.ehlo()

            print("Logging into Gmail...")

            server.login(
                gmail_user,
                gmail_password
            )

            print("Sending email...")

            server.send_message(
                message
            )

        print()
        print("✓ EMAIL SENT SUCCESSFULLY")
        print(f"From: {gmail_user}")
        print(f"To:   {gmail_to}")
        print(f"PDF:  {pdf_file}")

        return True

    except smtplib.SMTPAuthenticationError:

        print()
        print("❌ GMAIL AUTHENTICATION FAILED")
        print()
        print("Check:")
        print("1. GMAIL_USER")
        print("2. GMAIL_APP_PASSWORD")
        print("3. Gmail 2-Step Verification")
        print("4. Use a Gmail App Password, NOT normal password")

        return False

    except Exception as error:

        print()
        print("❌ EMAIL FAILED")
        print(f"Error: {error}")

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    separator()

    print("YOUTUBE TREND INTELLIGENCE GENERATOR")

    separator()

    print(f"Project root  : {PROJECT_ROOT}")
    print(f"Source folder : {SRC_DIR}")
    print(f"Data folder   : {DATA_DIR}")
    print(f"Reports folder: {REPORTS_DIR}")
    print(f"Summaries     : {SUMMARIES_DIR}")

    separator()

    # ========================================================
    # ENVIRONMENT
    # ========================================================

    check_environment()

    # ========================================================
    # STEP 1
    # ========================================================

    separator()

    print("STEP 1 - FETCHING YOUTUBE TREND DATA")

    separator()

    run_python_script(
        "youtube_agent.py"
    )

    youtube_data = (
        DATA_DIR /
        "youtube_trends.json"
    )

    if not youtube_data.exists():

        print("❌ YouTube trend data was not created:")
        print(youtube_data)

        sys.exit(1)

    print()
    print("✓ Trend data found:")
    print(youtube_data)

    # ========================================================
    # STEP 2
    # ========================================================

    separator()

    print("STEP 2 - GENERATING CONTENT IDEAS")

    separator()

    run_python_script(
        "idea_generator.py"
    )

    # ========================================================
    # IMPORTANT FIX
    # ========================================================
    #
    # idea_generator.py creates:
    #
    # summaries/youtube_ideas_YYYYMMDD_HHMMSS.json
    #
    # But old app.py expects:
    #
    # data/content_ideas.json
    #
    # We now automatically create the expected file.
    # ========================================================

    content_ideas = create_content_ideas()

    if not content_ideas.exists():

        print("❌ content_ideas.json was not created.")

        sys.exit(1)

    # ========================================================
    # STEP 3
    # ========================================================

    separator()

    print("STEP 3 - CREATING PDF")

    separator()

    pdf_file = create_pdf()

    if pdf_file is None:

        print("❌ PDF creation failed.")

        sys.exit(1)

    # ========================================================
    # STEP 4
    # ========================================================

    separator()

    print("STEP 4 - SENDING EMAIL")

    separator()

    email_sent = send_email(
        pdf_file
    )

    # Email failure does not delete the PDF.
    # GitHub Actions can still upload the PDF artifact.

    if not email_sent:

        print()
        print(
            "⚠ PDF was created successfully, "
            "but email was not sent."
        )

    # ========================================================
    # FINAL
    # ========================================================

    separator()

    print("GENERATION COMPLETED SUCCESSFULLY")

    separator()

    print()
    print("OUTPUT FILES")
    print("------------------------------")
    print(f"✓ {youtube_data}")
    print(f"✓ {content_ideas}")
    print(f"✓ {pdf_file}")

    if email_sent:
        print("✓ Email sent")
    else:
        print("⚠ Email not sent")

    separator()


if __name__ == "__main__":
    main()
