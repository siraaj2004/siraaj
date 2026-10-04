import json
import os
import smtplib
import ssl
import sys
import traceback
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import requests
from dotenv import load_dotenv
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
SUMMARIES_DIR = BASE_DIR / "summaries"

ENV_FILE = BASE_DIR / ".env"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

if ENV_FILE.exists():
    print("✓ Project .env found.")
    load_dotenv(ENV_FILE)
else:
    print("⚠ Project .env not found.")
    print("Using GitHub Actions environment variables.")


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_TO = os.getenv("GMAIL_TO")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


# ============================================================
# CONFIGURATION
# ============================================================

GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]

YOUTUBE_REGION = "IN"
YOUTUBE_CATEGORY = "10"
MAX_RESULTS = 50
REQUEST_TIMEOUT = 60


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

def check_environment():
    print()
    print("=" * 60)
    print("ENVIRONMENT CHECK")
    print("=" * 60)

    required = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "GMAIL_USER": GMAIL_USER,
        "GMAIL_TO": GMAIL_TO,
        "GMAIL_APP_PASSWORD": GMAIL_APP_PASSWORD,
    }

    missing = []

    for name, value in required.items():
        if value:
            print(f"✓ {name} found")
        else:
            print(f"✗ {name} missing")
            missing.append(name)

    if missing:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    print()
    print("ENVIRONMENT CHECK PASSED")


# ============================================================
# COLLECT YOUTUBE TRENDING VIDEOS
# ============================================================

def get_youtube_trending_videos():
    print()
    print("=" * 60)
    print("COLLECTING YOUTUBE TRENDING VIDEOS")
    print("=" * 60)

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": YOUTUBE_REGION,
        "videoCategoryId": YOUTUBE_CATEGORY,
        "maxResults": MAX_RESULTS,
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    print(
        f"YouTube API HTTP status: "
        f"{response.status_code}"
    )

    if response.status_code != 200:
        print("YouTube response:")
        print(response.text)

        raise RuntimeError(
            f"YouTube API failed with HTTP "
            f"{response.status_code}"
        )

    data = response.json()

    videos = []

    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})

        video_id = item.get("id")

        videos.append({
            "video_id": video_id,
            "title": snippet.get(
                "title",
                "Unknown Title",
            ),
            "channel": snippet.get(
                "channelTitle",
                "Unknown Channel",
            ),
            "published_at": snippet.get(
                "publishedAt",
                "",
            ),
            "description": snippet.get(
                "description",
                "",
            )[:1000],
            "tags": snippet.get(
                "tags",
                [],
            )[:20],
            "views": int(
                statistics.get(
                    "viewCount",
                    0,
                )
            ),
            "likes": int(
                statistics.get(
                    "likeCount",
                    0,
                )
            ),
            "comments": int(
                statistics.get(
                    "commentCount",
                    0,
                )
            ),
            "url": (
                "https://www.youtube.com/watch?v="
                f"{video_id}"
            ),
        })

    print(
        f"✓ Collected {len(videos)} trending videos"
    )

    raw_file = DATA_DIR / "youtube_trending_raw.json"

    with open(
        raw_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"✓ Saved: {raw_file}")

    processed_file = (
        DATA_DIR / "youtube_trending_processed.json"
    )

    with open(
        processed_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            videos,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"✓ Saved: {processed_file}")

    return videos


# ============================================================
# PREPARE DATA FOR GEMINI
# ============================================================

def prepare_gemini_data(videos):
    simplified = []

    for index, video in enumerate(
        videos,
        start=1,
    ):
        simplified.append({
            "rank": index,
            "title": video["title"],
            "channel": video["channel"],
            "views": video["views"],
            "likes": video["likes"],
            "comments": video["comments"],
            "published_at": video["published_at"],
            "description": video["description"],
            "tags": video["tags"],
            "url": video["url"],
        })

    return json.dumps(
        simplified,
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# GEMINI API
# ============================================================

def ask_gemini(prompt):
    print()
    print("Sending trend data to Gemini...")

    try:
        from google import genai
    except ImportError as error:
        raise RuntimeError(
            "google-genai package is missing. "
            "Add google-genai to requirements.txt."
        ) from error

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    last_error = None

    for model_name in GEMINI_MODELS:
        print(
            f"Trying Gemini model: "
            f"{model_name}"
        )

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )

            text = getattr(
                response,
                "text",
                None,
            )

            if text and text.strip():
                print(
                    f"✓ Gemini response received "
                    f"using {model_name}"
                )

                return text.strip()

            print(
                f"⚠ Empty Gemini response "
                f"from {model_name}"
            )

        except Exception as error:
            last_error = error

            print(
                f"⚠ Gemini model failed: "
                f"{model_name}"
            )
            print(str(error))

    raise RuntimeError(
        "All Gemini models failed.\n"
        f"Last error: {last_error}"
    )


# ============================================================
# GENERATE AI REPORT
# ============================================================

def generate_ai_report(videos):
    print()
    print("=" * 60)
    print("GENERATING AI TREND REPORT")
    print("=" * 60)

    trend_data = prepare_gemini_data(videos)

    prompt = f"""
You are an expert YouTube trend intelligence analyst.

Analyze the following current YouTube trending video data.

Create a practical report for a YouTube creator
who wants to make viral Indian/Telugu content.

Analyze:

1. Overall YouTube trends
2. Common content formats
3. Common topics
4. Viral title patterns
5. Viral hooks
6. Audience interests
7. Strong engagement patterns
8. Shorts opportunities
9. Long-form opportunities
10. Telugu/Indian opportunities
11. Comedy opportunities
12. Thriller/suspense opportunities

Then generate 10 ORIGINAL video ideas.

For every idea provide:

Title:
Concept:
Hook:
Why it could work:
Suggested format:

Finally provide the TOP 3 ideas
the creator should make first.

Do not copy existing titles.
Do not recommend copying another creator.

CURRENT TREND DATA:

{trend_data}
"""

    report = ask_gemini(prompt)

    if not report:
        raise RuntimeError(
            "Gemini generated an empty report."
        )

    return report


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):
    for marker in (
        "###",
        "##",
        "#",
        "**",
        "__",
        "`",
    ):
        text = text.replace(
            marker,
            "",
        )

    return text.strip()


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf(report):
    print()
    print("=" * 60)
    print("CREATING PDF REPORT")
    print("=" * 60)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    pdf_file = (
        REPORTS_DIR
        / f"youtube_trend_report_{timestamp}.pdf"
    )

    document = SimpleDocTemplate(
        str(pdf_file),
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        leading=25,
        spaceAfter=20,
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        spaceAfter=8,
    )

    story = [
        Paragraph(
            "YOUTUBE TREND INTELLIGENCE REPORT",
            title_style,
        ),
        Paragraph(
            datetime.now().strftime(
                "Generated on %d %B %Y at %I:%M %p"
            ),
            body_style,
        ),
        Spacer(1, 10),
    ]

    for line in clean_text(report).splitlines():
        line = line.strip()

        if not line:
            story.append(Spacer(1, 5))
            continue

        safe_line = (
            line
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        if (
            len(line) < 120
            and (
                (
                    len(line) >= 2
                    and line[:2].isdigit()
                )
                or line.endswith(":")
            )
        ):
            story.append(
                Paragraph(
                    safe_line,
                    heading_style,
                )
            )
        else:
            story.append(
                Paragraph(
                    safe_line,
                    body_style,
                )
            )

    document.build(story)

    print(f"✓ PDF created: {pdf_file}")

    return pdf_file


# ============================================================
# SEND EMAIL THROUGH GMAIL
# ============================================================

def send_email(pdf_file):
    print()
    print("=" * 60)
    print("SENDING EMAIL")
    print("=" * 60)

    message = EmailMessage()

    message["From"] = GMAIL_USER
    message["To"] = GMAIL_TO
    message["Subject"] = (
        "YouTube Trend Intelligence Report"
    )

    message.set_content(
        f"""
Hello,

Your latest YouTube Trend Intelligence report
has been generated successfully using Gemini AI.

The attached PDF contains:

• Current YouTube trends
• Viral content patterns
• Title and hook patterns
• Shorts opportunities
• Long-form opportunities
• Telugu/Indian opportunities
• Comedy opportunities
• Thriller opportunities
• 10 original video ideas
• Top 3 recommended ideas

Generated:
{datetime.now().strftime("%d %B %Y, %I:%M %p")}

Regards,
YouTube Trend Intelligence
"""
    )

    with open(
        pdf_file,
        "rb",
    ) as file:
        message.add_attachment(
            file.read(),
            maintype="application",
            subtype="pdf",
            filename=pdf_file.name,
        )

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        context=context,
    ) as server:
        server.login(
            GMAIL_USER,
            GMAIL_APP_PASSWORD,
        )

        server.send_message(message)

    print(
        f"✓ Email sent successfully to "
        f"{GMAIL_TO}"
    )


# ============================================================
# SAVE TEXT SUMMARY
# ============================================================

def save_summary(report):
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    summary_file = (
        SUMMARIES_DIR
        / f"youtube_trend_summary_{timestamp}.txt"
    )

    summary_file.write_text(
        report,
        encoding="utf-8",
    )

    print(
        f"✓ Summary saved: {summary_file}"
    )

    return summary_file


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("=" * 46)
    print(
        "STARTING YOUTUBE TREND INTELLIGENCE"
    )
    print("=" * 46)

    try:
        check_environment()

        videos = get_youtube_trending_videos()

        if not videos:
            raise RuntimeError(
                "No YouTube trending videos found."
            )

        report = generate_ai_report(videos)

        save_summary(report)

        pdf_file = create_pdf(report)

        send_email(pdf_file)

        print()
        print("=" * 60)
        print(
            "YOUTUBE TREND INTELLIGENCE COMPLETED"
        )
        print("=" * 60)
        print("✓ YouTube data collected")
        print("✓ Gemini AI report generated")
        print("✓ PDF created")
        print("✓ Email sent")
        print("=" * 60)

    except Exception as error:
        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print(str(error))
        print()
        print("Full traceback:")
        traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    main()

