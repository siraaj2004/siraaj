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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

JSON_FILE = DATA_DIR / "youtube_high_ctr_ideas.json"
PDF_FILE = DATA_DIR / "youtube_high_ctr_ideas.pdf"


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


def log(message=""):
    print(message, flush=True)


def check_environment():

    log("")
    log("=" * 60)
    log("CHECKING ENVIRONMENT")
    log("=" * 60)

    variables = {
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    }

    missing = []

    for name, value in variables.items():

        if value:
            log(f"{name}: OK")
        else:
            log(f"{name}: MISSING")
            missing.append(name)

    if missing:

        raise RuntimeError(
            "Missing GitHub Secrets: "
            + ", ".join(missing)
        )

    log("Environment check: OK")


def youtube_trends(region):

    log("")
    log(
        f"Collecting YouTube mostPopular data: {region}"
    )

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        url,
        params=params,
        timeout=60,
    )

    log(
        f"YouTube HTTP status: {response.status_code}"
    )

    if response.status_code >= 400:

        log(response.text[:3000])
        response.raise_for_status()

    data = response.json()

    videos = []

    for item in data.get("items", []):

        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        videos.append({
            "title": snippet.get("title", ""),
            "channel": snippet.get(
                "channelTitle",
                ""
            ),
            "published_at": snippet.get(
                "publishedAt",
                ""
            ),
            "views": int(
                stats.get(
                    "viewCount",
                    0
                ) or 0
            ),
            "likes": int(
                stats.get(
                    "likeCount",
                    0
                ) or 0
            ),
            "comments": int(
                stats.get(
                    "commentCount",
                    0
                ) or 0
            ),
            "region": region,
        })

    log(
        f"Collected {len(videos)} videos."
    )

    return videos


def openrouter(prompt, temperature=0.7):

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

    headers = {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube High CTR Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a YouTube entertainment "
                    "content strategist. "
                    "Return JSON only. "
                    "Never use Markdown fences."
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
        log(
            f"Model: {OPENROUTER_MODEL}"
        )
        log(
            f"Attempt: {attempt}"
        )

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=180,
            )

            log(
                f"HTTP status: {response.status_code}"
            )

            if response.status_code >= 400:

                log(response.text[:3000])

                if attempt == 3:
                    response.raise_for_status()

                continue

            data = response.json()

            choices = data.get(
                "choices",
                []
            )

            if not choices:
                continue

            content = (
                choices[0]
                .get("message", {})
                .get("content", "")
            )

            if not content:
                continue

            log("OpenRouter SUCCESS")

            log(
                "Model used: "
                + str(
                    data.get(
                        "model",
                        OPENROUTER_MODEL
                    )
                )
            )

            return content

        except Exception as error:

            log(
                f"OpenRouter error: {error}"
            )

            if attempt == 3:
                raise

    raise RuntimeError(
        "OpenRouter failed after 3 attempts."
    )


def parse_json(text):

    if not text:
        raise ValueError(
            "AI returned empty response."
        )

    text = text.strip()

    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```JSON",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.strip()

    try:
        return json.loads(text)

    except Exception:
        pass

    first = text.find("{")
    last = text.rfind("}")

    if first != -1 and last > first:

        candidate = text[
            first:last + 1
        ]

        try:
            return json.loads(
                candidate
            )

        except Exception:
            pass

    raise ValueError(
        "AI returned invalid JSON."
    )


def generate_report(india, worldwide):

    log("")
    log(
        "Generating HIGH CTR + YouTube ideas..."
    )

    prompt = f"""
Create a YouTube entertainment trend report.

Audience:
Indian viewers and Telugu viewers.

Create:
1. High CTR YouTube ideas.
2. YouTube Shorts ideas.
3. One final best idea.

Preferred genres:
- Thriller
- Mystery
- Suspense
- Comedy
- Relatable situations
- Unexpected but logical twists

Do not create boring, childish, random,
or meaningless ideas.

INDIA TRENDS:

{json.dumps(
    india[:50],
    ensure_ascii=False
)}

WORLDWIDE TRENDS:

{json.dumps(
    worldwide[:50],
    ensure_ascii=False
)}

Return ONLY JSON.

Use this structure:

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

Generate at least 10 long-form ideas
and 10 Shorts ideas.
"""

    raw = openrouter(
        prompt
    )

    try:

        result = parse_json(
            raw
        )

    except Exception as error:

        log("")
        log(
            "Initial JSON parsing failed."
        )
        log(str(error))

        log("")
        log(
            "ATTEMPTING JSON REPAIR"
        )

        repair_prompt = f"""
Repair this response into valid JSON.

Return ONLY JSON.
No Markdown.
No code fences.

Required keys:
market_summary
ideas
shorts_ideas
final_best_idea

Response:

{raw}
"""

        repaired = openrouter(
            repair_prompt,
            temperature=0.2
        )

        result = parse_json(
            repaired
        )

    if not isinstance(
        result,
        dict
    ):
        result = {}

    return result


def save_json(report):

    output = {
        "generated_at": datetime.now().isoformat(),
        **report
    }

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    log("")
    log("RESULT SAVED")
    log(str(JSON_FILE))

    return output


def clean_text(value):

    if value is None:
        return ""

    if isinstance(
        value,
        (dict, list)
    ):

        value = json.dumps(
            value,
            ensure_ascii=False
        )

    return html.escape(
        str(value)
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
            styles["Title"]
        )
    )

    story.append(
        Spacer(1, 20)
    )

    best = report.get(
        "final_best_idea",
        {}
    )

    story.append(
        Paragraph(
            "FINAL BEST IDEA",
            styles["Heading2"]
        )
    )

    fields = [
        "title",
        "genre",
        "english",
        "roman_telugu",
        "hook",
        "why_best",
        "ending",
    ]

    for field in fields:

        value = best.get(
            field,
            ""
        )

        if value:

            story.append(
                Paragraph(
                    f"<b>{field.upper()}</b><br/>"
                    f"{clean_text(value)}",
                    styles["BodyText"]
                )
            )

            story.append(
                Spacer(1, 10)
            )

    ideas = report.get(
        "ideas",
        []
    )

    if ideas:

        story.append(
            Paragraph(
                "HIGH CTR VIDEO IDEAS",
                styles["Heading2"]
            )
        )

        for number, idea in enumerate(
            ideas,
            start=1
        ):

            story.append(
                Paragraph(
                    f"<b>{number}. "
                    f"{clean_text(idea.get('title', ''))}"
                    f"</b>",
                    styles["Heading3"]
                )
            )

            for field in [
                "genre",
                "english",
                "roman_telugu",
                "hook",
                "why_best",
                "format",
                "ending",
            ]:

                value = idea.get(
                    field,
                    ""
                )

                if value:

                    story.append(
                        Paragraph(
                            f"<b>{field.upper()}</b><br/>"
                            f"{clean_text(value)}",
                            styles["BodyText"]
                        )
                    )

                    story.append(
                        Spacer(1, 7)
                    )

    shorts = report.get(
        "shorts_ideas",
        []
    )

    if shorts:

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "CURRENT SHORTS",
                styles["Heading2"]
            )
        )

        for number, idea in enumerate(
            shorts,
            start=1
        ):

            story.append(
                Paragraph(
                    f"<b>{number}. "
                    f"{clean_text(idea.get('title', ''))}"
                    f"</b>",
                    styles["Heading3"]
                )
            )

            for field in [
                "hook",
                "concept",
                "twist",
            ]:

                value = idea.get(
                    field,
                    ""
                )

                if value:

                    story.append(
                        Paragraph(
                            f"<b>{field.upper()}</b><br/>"
                            f"{clean_text(value)}",
                            styles["BodyText"]
                        )
                    )

                    story.append(
                        Spacer(1, 7)
                    )

    document.build(
        story
    )

    log(
        "PDF created successfully"
    )

    log(
        f"PDF: {PDF_FILE}"
    )


def send_email():

    log("")
    log("=" * 60)
    log("SENDING EMAIL THROUGH RESEND")
    log("=" * 60)

    if not PDF_FILE.exists():

        raise FileNotFoundError(
            f"PDF does not exist: {PDF_FILE}"
        )

    with open(
        PDF_FILE,
        "rb"
    ) as file:

        encoded = base64.b64encode(
            file.read()
        ).decode(
            "utf-8"
        )

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

        <p>
        Generated automatically by GitHub Actions.
        </p>
        """,
        "attachments": [
            {
                "filename": (
                    "youtube_high_ctr_ideas.pdf"
                ),
                "content": encoded
            }
        ]
    }

    headers = {
        "Authorization": (
            f"Bearer {RESEND_API_KEY}"
        ),
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://api.resend.com/emails",
        headers=headers,
        json=payload,
        timeout=60
    )

    log(
        "Resend HTTP status: "
        + str(response.status_code)
    )

    if response.status_code >= 400:

        log("")
        log("RESEND ERROR:")
        log(response.text)

        raise RuntimeError(
            "Resend failed: "
            + response.text
        )

    data = response.json()

    log("")
    log("EMAIL SENT SUCCESSFULLY")

    if data.get("id"):

        log(
            "Resend ID: "
            + str(data["id"])
        )


def main():

    log("")
    log("=" * 60)
    log("STARTING YOUTUBE HIGH CTR IDEA GENERATOR")
    log("=" * 60)

    check_environment()

    log("")
    log("1. Collecting India trends...")

    india = youtube_trends(
        "IN"
    )

    log("")
    log(
        "2. Collecting worldwide proxy trends..."
    )

    worldwide = youtube_trends(
        "US"
    )

    report = generate_report(
        india,
        worldwide
    )

    report = save_json(
        report
    )

    create_pdf(
        report
    )

    send_email()

    log("")
    log("=" * 60)
    log(
        "YOUTUBE HIGH CTR IDEA GENERATOR COMPLETED"
    )
    log("=" * 60)

    log(
        f"JSON: {JSON_FILE}"
    )

    log(
        f"PDF: {PDF_FILE}"
    )


if __name__ == "__main__":

    try:

        main()

    except Exception as error:

        log("")
        log("=" * 60)
        log("FATAL ERROR")
        log("=" * 60)

        log(
            f"{type(error).__name__}: {error}"
        )

        sys.exit(1)

