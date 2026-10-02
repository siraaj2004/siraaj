import os
import sys
import json
import html
from pathlib import Path
from datetime import datetime
from collections import Counter

import requests
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google import genai
from google.genai import types

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
OUTPUT_DIR = BASE_DIR / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

ORIGINAL_REPORT_FILE = BASE_DIR / "YouTube_Trend_Intelligence_Original.txt"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
PDF_FILE = OUTPUT_DIR / f"YouTube_Trend_Intelligence_{STAMP}.pdf"
JSON_FILE = OUTPUT_DIR / f"YouTube_Trend_Intelligence_{STAMP}.json"


# ============================================================
# ENV
# ============================================================

load_dotenv(ENV_FILE, override=True)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", "").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()


def validate_environment():
    required = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
    }

    missing = [k for k, v in required.items() if not v]

    if missing:
        raise RuntimeError(
            "Missing .env variables: " + ", ".join(missing)
        )


# ============================================================
# ORIGINAL REPORT
# ============================================================

def load_original_report():
    if not ORIGINAL_REPORT_FILE.exists():
        return ""

    try:
        return ORIGINAL_REPORT_FILE.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: could not read original report: {e}")
        return ""


# ============================================================
# YOUTUBE
# ============================================================

def get_youtube_client():
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def fetch_trending_videos(youtube, region_code, max_results=50):
    response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results,
    ).execute()

    videos = []

    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        videos.append({
            "video_id": item.get("id", ""),
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "category_id": snippet.get("categoryId", ""),
            "published_at": snippet.get("publishedAt", ""),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "description": snippet.get("description", "")[:700],
        })

    return videos


def fetch_category_names(youtube, category_ids):
    ids = list({str(x) for x in category_ids if x})
    if not ids:
        return {}

    response = youtube.videoCategories().list(
        part="snippet",
        id=",".join(ids),
    ).execute()

    return {
        str(item["id"]): item["snippet"]["title"]
        for item in response.get("items", [])
    }


def enrich_videos_with_categories(youtube, videos):
    category_map = fetch_category_names(
        youtube,
        [v.get("category_id") for v in videos],
    )

    for video in videos:
        video["category"] = category_map.get(
            str(video.get("category_id", "")),
            "Unknown",
        )

    return videos


def build_trend_summary(videos):
    """Build a trend summary safely even if an API response contains
    unexpected list/non-dict records."""
    safe_videos = [v for v in (videos or []) if isinstance(v, dict)]

    categories = Counter(
        str(v.get("category", "Unknown"))
        for v in safe_videos
    )

    top_videos = sorted(
        safe_videos,
        key=lambda x: int(x.get("views", 0) or 0),
        reverse=True,
    )[:20]

    return {
        "total_videos": len(safe_videos),
        "total_views": sum(
            int(v.get("views", 0) or 0) for v in safe_videos
        ),
        "top_categories": categories.most_common(),
        "top_videos": top_videos,
    }


def normalize_idea_list(value):
    """Return only dictionary-shaped ideas."""
    if not isinstance(value, list):
        return []

    cleaned = []
    for item in value:
        if isinstance(item, dict):
            cleaned.append(item)
        elif isinstance(item, list):
            # Gemini occasionally nests an idea list one level deeper.
            for nested in item:
                if isinstance(nested, dict):
                    cleaned.append(nested)

    return cleaned


def get_idea_list(result, preferred_keys):
    """Normalize Gemini object/array/nested output into a list of dict ideas."""
    if isinstance(result, list):
        return normalize_idea_list(result)

    if not isinstance(result, dict):
        return []

    # First check requested keys.
    for key in preferred_keys:
        value = result.get(key)
        ideas = normalize_idea_list(value)
        if ideas:
            return ideas

    # Then inspect one nested dictionary level.
    for value in result.values():
        if isinstance(value, dict):
            for key in preferred_keys:
                ideas = normalize_idea_list(value.get(key))
                if ideas:
                    return ideas

    # Finally, if the object itself looks like a single idea, accept it.
    if result.get("title") or result.get("logline"):
        return [result]

    return []


def extract_json_value(raw_text):
    """Safely parse Gemini JSON and accept either an object or a list."""
    if not raw_text:
        raise RuntimeError("Gemini returned an empty response.")

    text = raw_text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as first_error:
        # Gemini sometimes adds a small amount of text around valid JSON.
        decoder = json.JSONDecoder()
        for i, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                value, _ = decoder.raw_decode(text[i:])
                return value
            except json.JSONDecodeError:
                continue
        raise RuntimeError(
            "Gemini returned invalid/incomplete JSON: "
            f"{first_error}"
        ) from first_error


def gemini_json(client, prompt, temperature=0.9, max_output_tokens=30000):
    last_error = None

    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=temperature,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=max_output_tokens,
                ),
            )

            result = extract_json_value(response.text)

            # IMPORTANT: Gemini may legally return a JSON array even when
            # the prompt asks for a top-level object. Do not call .get()
            # on it; return it to the caller for shape normalization.
            return result

        except Exception as exc:
            last_error = exc
            print(f"    Gemini request {attempt}/3 failed: {exc}")

            if attempt < 3:
                prompt += """

IMPORTANT RETRY INSTRUCTION:
Return ONLY complete valid JSON.
The top-level response may be either the requested JSON object or array,
but it must be complete. Do not add markdown or explanations.
Keep descriptions concise so the response finishes before the token limit.
"""
                max_output_tokens = min(max_output_tokens, 18000)

    raise RuntimeError(f"Gemini failed after 3 attempts: {last_error}")


def get_idea_list(result, preferred_keys):
    """Normalize Gemini's object/array output into a Python list of ideas."""
    if isinstance(result, list):
        return result

    if isinstance(result, dict):
        for key in preferred_keys:
            value = result.get(key)
            if isinstance(value, list):
                return value

        # Also handle one nested object level, e.g. {"result": {"ideas": [...]}}.
        for value in result.values():
            if isinstance(value, dict):
                for key in preferred_keys:
                    nested = value.get(key)
                    if isinstance(nested, list):
                        return nested

    return []


# ============================================================
# CRITIC / RETENTION FILTER
# ============================================================

def build_critic_prompt(candidates):
    return f"""
You are the FINAL QUALITY GATE for a YouTube channel.

A previous AI generated these concepts. Your job is NOT to be
polite. Reject anything that feels generic, silly, predictable,
or like a writing exercise.

{QUALITY_RULES}

A concept is strong only if it has:
- a highly clickable contradiction
- a clear mystery question
- escalating uncertainty
- specific clues
- a believable false theory
- a reveal that reinterprets earlier clues
- an ending payoff
- a reason to watch until the end
- solo-shoot feasibility
- emotional or comedic payoff
- enough material for an actual 8-10 minute video when marked
  long-form.

Score internally from 0-10:
HOOK
CURIOSITY
ESCALATION
ORIGINALITY
LOGIC
RELATABILITY
PAYOFF
SOLO_SHOOT
RETENTION

REJECT any concept with:
- average internal score below 8
- weak reveal
- random coincidence
- generic object movement
- no meaningful escalation
- reveal obvious in first 30 seconds
- no reason for protagonist to continue
- comedy that is unrelated to the plot.

For surviving ideas, improve the writing if necessary.

Return exactly 12 final ideas.

Required JSON:
{{
  "approved_ideas": [
    {{
      "title": "",
      "genre": "",
      "logline": "",
      "hook": "",
      "normal_start": "",
      "strange_event": "",
      "mystery_question": "",
      "investigation": "",
      "escalation": "",
      "false_theory": "",
      "clues": ["", "", ""],
      "reveal": "",
      "ending_payoff": "",
      "content_summary": "",
      "video_outline": ["", "", "", "", "", "", ""],
      "target_audience": "",
      "estimated_duration": "",
      "shooting_difficulty": "",
      "viral_potential": "",
      "why_viewer_will_continue": "",
      "why_this_is_not_silly": ""
    }}
  ]
}}

CANDIDATES:
{json.dumps(candidates, ensure_ascii=False, indent=2)}
"""


def quality_gate(client, candidates):
    candidates = normalize_idea_list(candidates)

    if not candidates:
        raise RuntimeError("No usable candidate dictionaries were received.")

    prompt = build_critic_prompt(candidates)
    result = gemini_json(
        client,
        prompt,
        temperature=0.65,
        max_output_tokens=30000,
    )

    ideas = get_idea_list(result, ["approved_ideas", "ideas", "final_ideas"])

    if len(ideas) < 8:
        raise RuntimeError(
            f"Quality gate returned only {len(ideas)} ideas. "
            "Try running again."
        )

    return ideas[:12]


# ============================================================
# REPORT BUILDER
# ============================================================

def build_final_report(
    client,
    india_videos,
    worldwide_videos,
    original_report,
):
    print("[3/5] Generating 24 candidate concepts...")

    generation_prompt = build_generation_prompt(
        india_videos,
        worldwide_videos,
        original_report,
    )

    candidates_result = gemini_json(
        client,
        generation_prompt,
        temperature=0.95,
        max_output_tokens=30000,
    )

    candidates = get_idea_list(
        candidates_result,
        ["ideas", "candidate_ideas", "approved_ideas", "final_ideas"],
    )

    if not candidates:
        raise RuntimeError("Gemini returned no candidate ideas.")

    candidates = normalize_idea_list(candidates)

    if not candidates:
        raise RuntimeError(
            "Gemini returned JSON, but it contained no dictionary-shaped candidate ideas."
        )

    # Keep the requested 24 maximum while tolerating fewer valid results.
    candidates = candidates[:24]

    print(f"    Candidates received: {len(candidates)}")
    print("[4/5] Running strict audience/retention quality gate...")

    approved = quality_gate(client, candidates)
    approved = normalize_idea_list(approved)

    print(f"    Strong ideas after filtering: {len(approved)}")

    if not approved:
        raise RuntimeError("Quality gate returned no usable dictionary ideas.")

    trend_based = approved[:4]
    original = approved[4:8]
    crime = approved[8:10]
    shorts = approved[10:12]

    final_idea = approved[0]

    return {
        "report_title": "YouTube Trend Intelligence - High Engagement Edition",
        "executive_goal": {
            "goal": "Create highly engaging YouTube content with strong curiosity and retention.",
            "best_direction": "Relatable mystery + thriller escalation + logical reveal + natural comedy.",
            "best_idea_title": final_idea.get("title", ""),
            "best_idea_logline": final_idea.get("logline", ""),
            "reason": final_idea.get("why_viewer_will_continue", ""),
        },
        "india_trends": {
            "overview": "Trend signals collected from YouTube mostPopular for India.",
            "trending_topics": [],
            "trending_formats": [],
            "trending_genres": build_trend_summary(india_videos)["top_categories"],
            "evidence": build_trend_summary(india_videos)["top_videos"],
        },
        "worldwide_trends": {
            "overview": "US YouTube trends are used as a broad worldwide proxy; this is not a complete global measurement.",
            "trending_topics": [],
            "trending_formats": [],
            "trending_genres": build_trend_summary(worldwide_videos)["top_categories"],
            "evidence": build_trend_summary(worldwide_videos)["top_videos"],
        },
        "shorts_trend_ideas": shorts,
        "long_form_trend_ideas": trend_based,
        "crime_comedy_shorts_trend_based": crime,
        "crime_comedy_shorts_normal": original[:2],
        "thriller_comedy_trend_based": trend_based,
        "thriller_comedy_normal": original,
        "monetization_5_months_best_ideas": approved[:8],
        "final_best_idea": final_idea,
    }


# ============================================================
# PDF
# ============================================================

def setup_font():
    candidates = [
        Path("C:/Windows/Fonts/NotoSans-Regular.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ]

    for path in candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("ReportFont", str(path)))
                return "ReportFont"
            except Exception:
                pass

    return "Helvetica"


def make_styles(font):
    base = getSampleStyleSheet()

    return {
        "cover": ParagraphStyle(
            "Cover", parent=base["Title"], fontName=font,
            fontSize=25, leading=32, alignment=TA_CENTER,
            spaceAfter=12 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"], fontName=font,
            fontSize=10, leading=15, alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading1"], fontName=font,
            fontSize=18, leading=23, spaceBefore=9 * mm,
            spaceAfter=5 * mm,
        ),
        "idea": ParagraphStyle(
            "Idea", parent=base["Heading2"], fontName=font,
            fontSize=14, leading=19, spaceBefore=3 * mm,
            spaceAfter=4 * mm,
        ),
        "label": ParagraphStyle(
            "Label", parent=base["Normal"], fontName=font,
            fontSize=8.5, leading=12, textColor=colors.HexColor("#555555"),
            spaceBefore=2 * mm, spaceAfter=1 * mm,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName=font,
            fontSize=9, leading=14, spaceAfter=2.5 * mm,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName=font,
            fontSize=9, leading=13, leftIndent=5 * mm,
            firstLineIndent=-3 * mm, spaceAfter=1.5 * mm,
        ),
    }


def P(value):
    return html.escape(str(value if value is not None else ""))


def add_field(story, styles, label, value):
    if value is None or value == "" or value == []:
        return

    story.append(Paragraph(f"<b>{P(label)}</b>", styles["label"]))

    if isinstance(value, list):
        for item in value:
            story.append(
                Paragraph(f"• {P(item)}", styles["bullet"])
            )
    else:
        story.append(Paragraph(P(value), styles["body"]))


def add_idea(story, styles, idea, number):
    story.append(
        Paragraph(
            f"{number}. {P(idea.get('title', 'Untitled'))}",
            styles["idea"],
        )
    )

    fields = [
        ("Genre", "genre"),
        ("Logline", "logline"),
        ("Hook", "hook"),
        ("Normal Start", "normal_start"),
        ("Strange Event", "strange_event"),
        ("Mystery Question", "mystery_question"),
        ("Investigation", "investigation"),
        ("Escalation", "escalation"),
        ("False Theory", "false_theory"),
        ("Clues", "clues"),
        ("Reveal", "reveal"),
        ("Ending Payoff", "ending_payoff"),
        ("Content Summary", "content_summary"),
        ("Video Outline", "video_outline"),
        ("Target Audience", "target_audience"),
        ("Estimated Duration", "estimated_duration"),
        ("Shooting Difficulty", "shooting_difficulty"),
        ("Viral Potential", "viral_potential"),
        ("Why Viewer Will Continue", "why_viewer_will_continue"),
        ("Why This Is Not Silly", "why_this_is_not_silly"),
    ]

    for label, key in fields:
        add_field(story, styles, label, idea.get(key))


def create_pdf(report):
    font = setup_font()
    styles = make_styles(font)

    doc = SimpleDocTemplate(
        str(PDF_FILE),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    story = []

    story.append(Spacer(1, 25 * mm))
    story.append(
        Paragraph(
            P(report.get("report_title", "YouTube Trend Intelligence")),
            styles["cover"],
        )
    )
    story.append(
        Paragraph(
            "HIGH-ENGAGEMENT STORY ENGINE",
            styles["subtitle"],
        )
    )
    story.append(
        Paragraph(
            "Built to reject boring, predictable and random concepts.",
            styles["subtitle"],
        )
    )
    story.append(PageBreak())

    executive = report.get("executive_goal", {})
    story.append(Paragraph("Executive Direction", styles["section"]))
    add_field(story, styles, "Goal", executive.get("goal"))
    add_field(story, styles, "Best Direction", executive.get("best_direction"))
    add_field(story, styles, "Best Idea", executive.get("best_idea_title"))
    add_field(story, styles, "Best Logline", executive.get("best_idea_logline"))
    add_field(story, styles, "Why It Can Hold Attention", executive.get("reason"))

    sections = [
        ("Long-Form Trend Ideas", "long_form_trend_ideas"),
        ("Long-Form Original Ideas", "thriller_comedy_normal"),
        ("Crime-Comedy Ideas", "crime_comedy_shorts_trend_based"),
        ("Shorts Ideas", "shorts_trend_ideas"),
        ("Best Ideas for the Next 5 Months", "monetization_5_months_best_ideas"),
    ]

    for title, key in sections:
        story.append(PageBreak())
        story.append(Paragraph(title, styles["section"]))

        for i, idea in enumerate(report.get(key, []), 1):
            add_idea(story, styles, idea, i)
            story.append(HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#cccccc"),
                spaceBefore=2 * mm,
                spaceAfter=4 * mm,
            ))

    story.append(PageBreak())
    story.append(Paragraph("FINAL BEST IDEA", styles["section"]))
    add_idea(story, styles, report.get("final_best_idea", {}), 1)

    doc.build(story)

    return PDF_FILE


# ============================================================
# JSON
# ============================================================

def save_json(report):
    JSON_FILE.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# ============================================================
# RESEND
# ============================================================

def send_email(pdf_path, report):
    print("[5/5] Sending PDF by email...")

    pdf_bytes = pdf_path.read_bytes()

    payload = {
        "from": FROM_EMAIL,
        "to": [RECIPIENT_EMAIL],
        "subject": "YouTube High-Engagement Trend Intelligence",
        "html": f"""
        <h2>YouTube High-Engagement Trend Intelligence</h2>
        <p><b>Best idea:</b>
        {html.escape(report.get("final_best_idea", {}).get("title", ""))}
        </p>
        <p>The attached report was generated using a two-stage
        candidate + quality-gate process.</p>
        """,
        "attachments": [
            {
                "filename": pdf_path.name,
                "content": __import__("base64").b64encode(pdf_bytes).decode(),
            }
        ],
    }

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"Resend error {response.status_code}: {response.text}"
        )

    print("    Email sent successfully.")


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("=" * 72)
    print("YOUTUBE HIGH-ENGAGEMENT IDEA GENERATOR")
    print("=" * 72)

    validate_environment()

    original_report = load_original_report()

    print("[1/5] Connecting to YouTube...")
    youtube = get_youtube_client()

    print("[2/5] Collecting India + worldwide-proxy trends...")
    india = fetch_trending_videos(youtube, "IN", 50)
    worldwide = fetch_trending_videos(youtube, "US", 50)

    india = [v for v in india if isinstance(v, dict)]
    worldwide = [v for v in worldwide if isinstance(v, dict)]

    india = enrich_videos_with_categories(youtube, india)
    worldwide = enrich_videos_with_categories(youtube, worldwide)

    print(f"    India videos: {len(india)}")
    print(f"    Worldwide proxy videos: {len(worldwide)}")

    client = genai.Client(api_key=GEMINI_API_KEY)

    report = build_final_report(
        client,
        india,
        worldwide,
        original_report,
    )

    print("    Creating PDF...")
    create_pdf(report)
    save_json(report)

    send_email(PDF_FILE, report)

    print()
    print("=" * 72)
    print("DONE")
    print("=" * 72)
    print(f"PDF : {PDF_FILE}")
    print(f"JSON: {JSON_FILE}")
    print()
    print("FINAL BEST IDEA:")
    print(report.get("final_best_idea", {}).get("title", ""))
    print()
    print("The generator now uses:")
    print("  1. 24 candidate concepts")
    print("  2. Strict retention/logic filtering")
    print("  3. Final 12 strong concepts")
    print("  4. Logical planted clues + reveal")
    print("  5. Anti-silly quality rules")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 72)
        print("ERROR")
        print("=" * 72)
        print(f"{type(e).__name__}: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)
