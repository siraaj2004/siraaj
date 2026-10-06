````python
import os
import sys
import json
import base64
import html
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

JSON_FILE = DATA_DIR / "youtube_high_ctr_ideas.json"
PDF_FILE = DATA_DIR / "youtube_high_ctr_ideas.pdf"


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(BASE_DIR / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", "").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
).strip()


# ============================================================
# LOGGING
# ============================================================

def log(message=""):
    print(message, flush=True)


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

def validate_environment():

    log("")
    log("=" * 60)
    log("ENVIRONMENT CHECK")
    log("=" * 60)

    required = {
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    }

    missing = []

    for name, value in required.items():

        if value:
            log(f"{name}: OK")
        else:
            log(f"{name}: MISSING")
            missing.append(name)

    if missing:

        log("")
        log("ERROR: Missing GitHub Secrets:")

        for item in missing:
            log(f"  - {item}")

        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    log("")
    log("Environment check: OK")


# ============================================================
# YOUTUBE TREND COLLECTION
# ============================================================

def collect_youtube_trends(region_code, max_results=50):

    log("")
    log(f"Collecting YouTube mostPopular data: {region_code}")

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        url,
        params=params,
        timeout=60,
    )

    log(f"YouTube HTTP status: {response.status_code}")

    if response.status_code >= 400:
        log(response.text[:2000])
        response.raise_for_status()

    data = response.json()

    videos = []

    for item in data.get("items", []):

        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})

        video = {
            "video_id": item.get("id", ""),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "category_id": snippet.get("categoryId", ""),
            "view_count": int(
                statistics.get("viewCount", 0) or 0
            ),
            "like_count": int(
                statistics.get("likeCount", 0) or 0
            ),
            "comment_count": int(
                statistics.get("commentCount", 0) or 0
            ),
            "region": region_code,
        }

        if video["title"]:
            videos.append(video)

    log(f"Collected {len(videos)} videos.")

    return videos


# ============================================================
# CLEAN TRENDS
# ============================================================

def prepare_trends(india_videos, worldwide_videos):

    def clean(videos):

        result = []

        for video in videos:

            result.append({
                "title": video.get("title", ""),
                "channel": video.get("channel_title", ""),
                "views": video.get("view_count", 0),
                "likes": video.get("like_count", 0),
                "comments": video.get("comment_count", 0),
                "published_at": video.get("published_at", ""),
                "region": video.get("region", ""),
            })

        return result

    return {
        "india": clean(india_videos),
        "worldwide": clean(worldwide_videos),
    }


# ============================================================
# OPENROUTER REQUEST
# ============================================================

def call_openrouter(prompt, temperature=0.7):

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube High CTR Idea Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert YouTube entertainment "
                    "content strategist. "
                    "Return valid JSON only. "
                    "Never use Markdown code fences. "
                    "Never write explanations outside JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": temperature,
        "max_tokens": 12000,
    }

    for attempt in range(1, 4):

        log("")
        log("OPENROUTER REQUEST")
        log(f"Trying OpenRouter model: {OPENROUTER_MODEL}")
        log(f"Attempt: {attempt}")

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=180,
            )

            log(f"HTTP status: {response.status_code}")

            if response.status_code >= 400:

                log("OpenRouter error:")
                log(response.text[:3000])

                if attempt == 3:
                    response.raise_for_status()

                continue

            data = response.json()

            choices = data.get("choices", [])

            if not choices:
                log("No choices returned by OpenRouter.")
                continue

            message = choices[0].get("message", {})

            content = message.get("content", "")

            if not content:
                log("OpenRouter returned empty content.")
                continue

            log("OpenRouter SUCCESS")

            log(
                f"Model used: "
                f"{data.get('model', OPENROUTER_MODEL)}"
            )

            return content

        except Exception as error:

            log(f"OpenRouter attempt failed: {error}")

            if attempt == 3:
                raise

    raise RuntimeError(
        "OpenRouter failed after 3 attempts."
    )


# ============================================================
# EXTRACT JSON
# ============================================================

def extract_json(text):

    if not text:
        raise ValueError(
            "AI returned an empty response."
        )

    text = text.strip()

    # Remove accidental Markdown fences
    text = text.replace("```json", "")
    text = text.replace("```JSON", "")
    text = text.replace("```python", "")
    text = text.replace("```", "")
    text = text.strip()

    # Try complete response
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end > start:

        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Find array
    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end > start:

        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    raise ValueError(
        "AI returned invalid JSON."
    )


# ============================================================
# NORMALIZE RESULT
# ============================================================

def normalize_result(result):

    if not isinstance(result, dict):
        result = {}

    ideas = result.get("ideas", [])

    if not isinstance(ideas, list):
        ideas = []

    shorts = result.get("shorts_ideas", [])

    if not isinstance(shorts, list):
        shorts = []

    market_summary = result.get(
        "market_summary",
        {}
    )

    if not isinstance(market_summary, dict):
        market_summary = {}

    final_best = result.get(
        "final_best_idea",
        {}
    )

    if not isinstance(final_best, dict):
        final_best = {}

    return {
        "generated_at": datetime.now().isoformat(),
        "market_summary": {
            "india": market_summary.get(
                "india",
                []
            ),
            "worldwide": market_summary.get(
                "worldwide",
                []
            ),
        },
        "ideas": ideas,
        "shorts_ideas": shorts,
        "final_best_idea": final_best,
    }


# ============================================================
# GENERATE IDEAS
# ============================================================

def generate_ideas(trends):

    log("")
    log("3. Generating monetization strategy...")
    log("")
    log("4. Generating HIGH CTR + YouTube ideas...")

    prompt = f"""
Create a high-engagement YouTube entertainment report.

TARGET:
- Indian audience
- Telugu audience
- Worldwide entertainment trends
- YouTube Shorts
- 8-10 minute YouTube videos

STYLE:
- Interesting
- High curiosity
- Strong hooks
- Thriller
- Mystery
- Suspense
- Comedy
- Relatable situations
- Logical unexpected endings

DO NOT create:
- boring ideas
- random nonsense
- childish ideas
- impossible concepts
- generic ideas

INDIA TRENDS:

{json.dumps(
    trends["india"][:50],
    ensure_ascii=False
)}

WORLDWIDE TRENDS:

{json.dumps(
    trends["worldwide"][:50],
    ensure_ascii=False
)}

Return ONLY valid JSON.

Use exactly this structure:

{{
  "market_summary": {{
    "india": [],
    "worldwide": []
  }},

  "ideas": [
    {{
      "title": "",
      "genre": "",
      "english": "",
      "roman_telugu": "",
      "hook": "",
      "why_best": "",
      "format": "",
      "ending": ""
    }}
  ],

  "shorts_ideas": [
    {{
      "title": "",
      "hook": "",
      "concept": "",
      "twist": ""
    }}
  ],

  "final_best_idea": {{
    "title": "",
    "genre": "",
    "english": "",
    "roman_telugu": "",
    "hook": "",
    "why_best": "",
    "ending": ""
  }}
}}

Generate at least 10 strong long-form ideas
and at least 10 Shorts ideas.
"""

    raw = call_openrouter(prompt)

    try:

        result = extract_json(raw)

        log("")
        log("JSON parsed successfully.")

    except Exception as error:

        log("")
        log("Initial JSON parsing failed:")
        log(str(error))

        log("")
        log("ATTEMPTING JSON REPAIR")

        repair_prompt = f"""
Convert the following AI response into valid JSON.

Return ONLY JSON.
Do not use Markdown.
Do not use code fences.

Required keys:

market_summary
ideas
shorts_ideas
final_best_idea

AI RESPONSE:

{raw}
"""

        repaired = call_openrouter(
            repair_prompt,
            temperature=0.2,
        )

        result = extract_json(repaired)

    return normalize_result(result)


# ============================================================
# SAVE JSON
# ============================================================

def save_json(report):

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    log("")
    log("RESULT SAVED")
    log(str(JSON_FILE))


# ============================================================
# PDF
# ============================================================

def safe_text(value):

    if value is None:
        return ""

    if isinstance(value, (dict, list)):

        value = json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )

    value = str(value)

    return html.escape(
        value
    ).replace(
        "\n",
        "<br/>"
    )


def create_pdf(report):

    log("")
    log("=" * 60)
    log("CREATING PDF")
    log("=" * 60)

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    title_style.alignment = TA_CENTER

    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]

    document = SimpleDocTemplate(
        str(PDF_FILE),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    story = []

    story.append(
        Paragraph(
            "YOUTUBE HIGH CTR IDEA REPORT",
            title_style,
        )
    )

    story.append(
        Spacer(1, 20)
    )

    story.append(
        Paragraph(
            "Generated: "
            + safe_text(
                report.get(
                    "generated_at",
                    ""
                )
            ),
            body_style,
        )
    )

    story.append(
        Spacer(1, 20)
    )

    # --------------------------------------------------------
    # FINAL BEST IDEA
    # --------------------------------------------------------

    best = report.get(
        "final_best_idea",
        {}
    )

    story.append(
        Paragraph(
            "FINAL BEST IDEA",
            heading_style,
        )
    )

    for key in [
        "title",
        "genre",
        "english",
        "roman_telugu",
        "hook",
        "why_best",
        "ending",
    ]:

        value = best.get(key, "")

        if value:

            story.append(
                Paragraph(
                    f"<b>{key.upper()}</b><br/>"
                    f"{safe_text(value)}",
                    body_style,
                )
            )

            story.append(
                Spacer(1, 10)
            )

    story.append(PageBreak())

    # --------------------------------------------------------
    # LONG FORM IDEAS
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "HIGH CTR VIDEO IDEAS",
            heading_style,
        )
    )

    ideas = report.get(
        "ideas",
        []
    )

    for index, idea in enumerate(
        ideas,
        start=1
    ):

        story.append(
            Paragraph(
                f"<b>{index}. "
                f"{safe_text(idea.get('title', ''))}"
                f"</b>",
                heading_style,
            )
        )

        for key in [
            "genre",
            "english",
            "roman_telugu",
            "hook",
            "why_best",
            "format",
            "ending",
        ]:

            value = idea.get(
                key,
                ""
            )

            if value:

                story.append(
                    Paragraph(
                        f"<b>{key.upper()}</b><br/>"
                        f"{safe_text(value)}",
                        body_style,
                    )
                )

                story.append(
                    Spacer(1, 8)
                )

        story.append(
            Spacer(1, 15)
        )

    # --------------------------------------------------------
    # SHORTS
    # --------------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "CURRENT SHORTS",
            heading_style,
        )
    )

    shorts = report.get(
        "shorts_ideas",
        []
    )

    for index, idea in enumerate(
        shorts,
        start=1
    ):

        story.append(
            Paragraph(
                f"<b>{index}. "
                f"{safe_text(idea.get('title', ''))}"
                f"</b>",
                heading_style,
            )
        )

        for key in [
            "hook",
            "concept",
            "twist",
        ]:

            value = idea.get(
                key,
                ""
            )

            if value:

                story.append(
                    Paragraph(
                        f"<b>{key.upper()}</b><br/>"
                        f"{safe_text(value)}",
                        body_style,
                    )
                )

                story.append(
                    Spacer(1, 8)
                )

    document.build(story)

    log("PDF created successfully")
    log(f"PDF FILE: {PDF_FILE}")


# ============================================================
# SEND EMAIL WITH RESEND
# ============================================================

def send_email():

    log("")
    log("=" * 60)
    log("SENDING EMAIL THROUGH RESEND")
    log("=" * 60)

    if not RESEND_API_KEY:
        raise RuntimeError(
            "RESEND_API_KEY is missing."
        )

    if not FROM_EMAIL:
        raise RuntimeError(
            "FROM_EMAIL is missing."
        )

    if not RECIPIENT_EMAIL:
        raise RuntimeError(
            "RECIPIENT_EMAIL is missing."
        )

    if not PDF_FILE.exists():

        raise FileNotFoundError(
            f"PDF not found: {PDF_FILE}"
        )

    with open(
        PDF_FILE,
        "rb"
    ) as file:

        pdf_data = file.read()

    pdf_base64 = base64.b64encode(
        pdf_data
    ).decode("utf-8")

    payload = {
        "from": FROM_EMAIL,
        "to": [
            RECIPIENT_EMAIL
        ],
        "subject": (
            "YouTube High CTR Ideas Report - "
            + datetime.now().strftime(
                "%Y-%m-%d"
            )
        ),
        "html": """
        <h2>YouTube High CTR Idea Report</h2>

        <p>
        Your latest YouTube trend analysis
        and high CTR ideas are attached.
        </p>

        <p>The report contains:</p>

        <ul>
            <li>India YouTube trends</li>
            <li>Worldwide trends</li>
            <li>High CTR video ideas</li>
            <li>YouTube Shorts ideas</li>
            <li>Final best idea</li>
        </ul>

        <p>
        Generated automatically by GitHub Actions.
        </p>
        """,
        "attachments": [
            {
                "filename": "youtube_high_ctr_ideas.pdf",
                "content": pdf_base64,
            }
        ],
    }

    headers = {
        "Authorization": (
            f"Bearer {RESEND_API_KEY}"
        ),
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://api.resend.com/emails",
        headers=headers,
        json=payload,
        timeout=60,
    )

    log(
        f"Resend HTTP status: "
        f"{response.status_code}"
    )

    if response.status_code >= 400:

        log("")
        log("RESEND ERROR:")
        log(response.text)

        raise RuntimeError(
            "Resend email failed: "
            + response.text
        )

    try:
        resend_data = response.json()
    except Exception:
        resend_data = {}

    log("")
    log("EMAIL SENT SUCCESSFULLY")

    if resend_data.get("id"):

        log(
            f"Resend ID: "
            f"{resend_data['id']}"
        )


# ============================================================
# DISPLAY BEST IDEA
# ============================================================

def display_final_idea(report):

    best = report.get(
        "final_best_idea",
        {}
    )

    log("")
    log("=" * 60)
    log("HIGH CTR IDEA")
    log("=" * 60)

    log(
        f"TITLE: "
        f"{best.get('title', '')}"
    )

    log(
        f"GENRE: "
        f"{best.get('genre', '')}"
    )

    log(
        f"ENGLISH: "
        f"{best.get('english', '')}"
    )

    log(
        f"ROMAN TELUGU: "
        f"{best.get('roman_telugu', '')}"
    )

    log(
        f"HOOK: "
        f"{best.get('hook', '')}"
    )

    log(
        f"WHY BEST: "
        f"{best.get('why_best', '')}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    log("")
    log("=" * 60)
    log("STARTING YOUTUBE HIGH CTR IDEA GENERATOR")
    log("=" * 60)

    # 1. Environment
    validate_environment()

    # 2. India
    log("")
    log("1. Collecting India trends...")

    india_videos = collect_youtube_trends(
        "IN",
        50
    )

    # 3. Worldwide proxy
    log("")
    log(
        "2. Collecting worldwide proxy trends..."
    )

    worldwide_videos = collect_youtube_trends(
        "US",
        50
    )

    # 4. Prepare trends
    trends = prepare_trends(
        india_videos,
        worldwide_videos
    )

    # 5. Generate ideas
    report = generate_ideas(
        trends
    )

    # 6. Save JSON
    save_json(
        report
    )

    # 7. Display result
    display_final_idea(
        report
    )

    # 8. Create PDF
    create_pdf(
        report
    )

    # 9. Send email
    send_email()

    # 10. Finished
    log("")
    log("=" * 60)
    log(
        "YOUTUBE HIGH CTR IDEA GENERATOR COMPLETED"
    )
    log("=" * 60)

    log("")
    log(
        f"JSON: {JSON_FILE}"
    )

    log(
        f"PDF : {PDF_FILE}"
    )

    log(
        f"MAIL: {RECIPIENT_EMAIL}"
    )

    log("")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        log("")
        log("Process interrupted.")

        sys.exit(130)

    except Exception as error:

        log("")
        log("=" * 60)
        log("FATAL ERROR")
        log("=" * 60)

        log(
            f"{type(error).__name__}: "
            f"{error}"
        )

        log("")

        sys.exit(1)
````
