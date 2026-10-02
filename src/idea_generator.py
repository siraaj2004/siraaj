import os
import sys
import json
import base64
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
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    HRFlowable,
)

from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"

OUTPUT_DIR = BASE_DIR / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

ORIGINAL_REPORT_FILE = (
    BASE_DIR / "YouTube_Trend_Intelligence_Original.txt"
)

DATE_STRING = datetime.now().strftime("%Y%m%d_%H%M%S")

PDF_FILE = (
    OUTPUT_DIR /
    f"YouTube_Trend_Intelligence_{DATE_STRING}.pdf"
)

JSON_FILE = (
    OUTPUT_DIR /
    f"YouTube_Trend_Intelligence_{DATE_STRING}.json"
)


# ============================================================
# START
# ============================================================

print()
print("=" * 70)
print("YOUTUBE TREND INTELLIGENCE + ENGAGING IDEA GENERATOR")
print("=" * 70)
print()

print("Project folder:")
print(BASE_DIR)

print()

print("Looking for .env:")
print(ENV_FILE)


# ============================================================
# LOAD ENV
# ============================================================

if not ENV_FILE.exists():

    print()
    print("ERROR: .env file was not found.")
    print()
    print("Create:")
    print(ENV_FILE)
    print()

    sys.exit(1)


load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)

print()
print(".env loaded successfully.")


# ============================================================
# ENV VARIABLES
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
# VALIDATE ENV
# ============================================================

def validate_environment():

    variables = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
    }

    missing = [
        key
        for key, value in variables.items()
        if not value
    ]

    if missing:

        print()
        print("=" * 70)
        print("ENVIRONMENT VARIABLE ERROR")
        print("=" * 70)
        print()

        for item in missing:
            print(f"❌ {item}")

        print()

        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    print()
    print("Environment variables loaded:")

    for key in variables:
        print(f"  ✅ {key}")

    print()


# ============================================================
# LOAD ORIGINAL REPORT
# ============================================================

def load_original_report():

    if not ORIGINAL_REPORT_FILE.exists():

        print()
        print("No original report found.")
        print("Continuing with a new report.")
        print()

        return ""

    try:

        content = ORIGINAL_REPORT_FILE.read_text(
            encoding="utf-8"
        )

        print()
        print("Original report loaded:")
        print(ORIGINAL_REPORT_FILE)
        print(
            f"Characters: {len(content):,}"
        )
        print()

        return content

    except Exception as error:

        print(
            f"Could not read original report: {error}"
        )

        return ""


# ============================================================
# YOUTUBE API
# ============================================================

def get_youtube_client():

    return build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY
    )


def fetch_trending_videos(
    youtube,
    region_code,
    max_results=50
):

    response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results
    ).execute()

    videos = []

    for item in response.get(
        "items",
        []
    ):

        snippet = item.get(
            "snippet",
            {}
        )

        statistics = item.get(
            "statistics",
            {}
        )

        videos.append({

            "video_id":
                item.get(
                    "id",
                    ""
                ),

            "title":
                snippet.get(
                    "title",
                    ""
                ),

            "channel":
                snippet.get(
                    "channelTitle",
                    ""
                ),

            "category_id":
                snippet.get(
                    "categoryId",
                    ""
                ),

            "published_at":
                snippet.get(
                    "publishedAt",
                    ""
                ),

            "views":
                int(
                    statistics.get(
                        "viewCount",
                        0
                    )
                ),

            "likes":
                int(
                    statistics.get(
                        "likeCount",
                        0
                    )
                ),

            "comments":
                int(
                    statistics.get(
                        "commentCount",
                        0
                    )
                ),

            "description":
                snippet.get(
                    "description",
                    ""
                )[:1000],
        })

    return videos


def fetch_category_names(
    youtube,
    category_ids
):

    category_ids = list(
        set(
            str(x)
            for x in category_ids
            if x
        )
    )

    if not category_ids:
        return {}

    response = youtube.videoCategories().list(
        part="snippet",
        id=",".join(category_ids)
    ).execute()

    mapping = {}

    for item in response.get(
        "items",
        []
    ):

        mapping[
            str(item["id"])
        ] = item["snippet"]["title"]

    return mapping


def enrich_videos_with_categories(
    youtube,
    videos
):

    category_ids = [
        video.get(
            "category_id"
        )
        for video in videos
    ]

    category_map = fetch_category_names(
        youtube,
        category_ids
    )

    for video in videos:

        video["category"] = (
            category_map.get(
                str(
                    video.get(
                        "category_id",
                        ""
                    )
                ),
                "Unknown"
            )
        )

    return videos


# ============================================================
# TREND SUMMARY
# ============================================================

def build_trend_summary(videos):

    categories = Counter(
        video.get(
            "category",
            "Unknown"
        )
        for video in videos
    )

    total_views = sum(
        video.get(
            "views",
            0
        )
        for video in videos
    )

    top_videos = sorted(
        videos,
        key=lambda x: x.get(
            "views",
            0
        ),
        reverse=True
    )[:20]

    return {

        "total_videos":
            len(videos),

        "total_views":
            total_views,

        "top_categories":
            categories.most_common(),

        "top_videos":
            top_videos,
    }


# ============================================================
# ENGAGING IDEA GENERATION PROMPT
# ============================================================

def build_prompt(
    india_videos,
    worldwide_videos,
    original_report
):

    india_summary = build_trend_summary(
        india_videos
    )

    worldwide_summary = build_trend_summary(
        worldwide_videos
    )

    original_section = ""

    if original_report.strip():

        original_section = f"""

============================================================
PREVIOUS REPORT / MEMORY
============================================================

Use this previous report for continuity and inspiration.

DO NOT blindly repeat previous ideas.

Find patterns that worked and create NEW concepts.

Avoid:
- duplicate titles
- duplicate premises
- slightly renamed old ideas
- recycled twists

PREVIOUS REPORT:

{original_report}

============================================================
END PREVIOUS REPORT
============================================================
"""

    prompt = f"""

You are a PROFESSIONAL YOUTUBE STORY DEVELOPMENT WRITER.

You are NOT a generic AI idea generator.

Your job is to create YouTube concepts that make viewers
STOP scrolling and think:

"WHAT IS HAPPENING?"

"I NEED TO KNOW THE ANSWER."

"WAIT... THAT DOESN'T MAKE SENSE."

The creator wants ORIGINAL, ENGAGING, SHOOTABLE stories.

============================================================
CREATOR PROFILE
============================================================

The creator is a solo filmmaker.

Typical production:

- one actor
- one person on camera
- simple locations
- terrace
- apartment
- room
- lobby
- staircase
- nearby street
- morning/daylight
- static camera possible
- minimal equipment
- no expensive VFX
- no second actor required

Preferred genres:

- thriller
- mystery
- suspense
- comedy
- crime-comedy
- thriller + comedy

Audience:

- Telugu audience
- Indian audience
- normal YouTube viewers

The story must feel REAL.

============================================================
MOST IMPORTANT RULE
============================================================

DO NOT CREATE SILLY IDEAS.

Reject concepts like:

"My chair moved."

"Someone knocked."

"I saw a shadow."

"My phone disappeared."

"I heard a sound."

These are NOT stories by themselves.

The event must lead to a meaningful question,
investigation and payoff.

============================================================
THE STORY ENGINE
============================================================

Every idea must follow this structure:

RELATABLE NORMAL LIFE

↓

SMALL STRANGE EVENT

↓

CLEAR MYSTERY QUESTION

↓

INVESTIGATION

↓

SECOND CLUE

↓

ESCALATION

↓

FALSE EXPLANATION

↓

NEW CONTRADICTION

↓

FINAL CLUE

↓

LOGICAL REVEAL

↓

COMEDY / EMOTIONAL / THRILLER PAYOFF

============================================================
1. RELATABLE START
============================================================

Begin with something normal.

Examples:

- going to the terrace
- drying clothes
- checking a water tank
- drinking tea
- charging a phone
- working on laptop
- preparing for work
- checking a parcel
- cleaning
- taking a selfie
- checking CCTV
- looking for keys
- receiving a delivery
- checking a bike
- using an elevator

The first scene should feel ordinary.

============================================================
2. STRANGE EVENT
============================================================

Something specific happens.

BAD:

"Something strange happened."

GOOD:

"I left my laptop facing the wall.
When I returned, the laptop was facing the camera."

Specificity creates curiosity.

============================================================
3. MYSTERY QUESTION
============================================================

The viewer must immediately have a question.

Examples:

Who changed it?

How did they enter?

Why would someone do this?

Did I accidentally miss something?

Why does this keep happening?

Who knew I was here?

How did this object appear?

What happened before I arrived?

============================================================
4. ESCALATION
============================================================

The mystery cannot stay at the same level.

Example:

EVENT 1:
Chair moved.

EVENT 2:
Chair moved again.

EVENT 3:
Camera shows nobody entering.

EVENT 4:
A small object appears in the recording.

EVENT 5:
The protagonist realizes the object was already in
his room.

Now the viewer NEEDS the answer.

============================================================
5. FALSE EXPLANATION
============================================================

The protagonist should form a believable theory.

Examples:

Maybe neighbour entered.

Maybe someone has a spare key.

Maybe the security guard moved it.

Maybe the camera missed someone.

Maybe I accidentally did it.

But later evidence must challenge that theory.

============================================================
6. CLUES
============================================================

Plant clues before the reveal.

Every important clue must have a purpose.

The final reveal must make the audience think:

"OH! THAT'S WHY."

Not:

"Where did that come from?"

============================================================
7. LOGICAL REVEAL
============================================================

The ending should explain earlier events.

Do NOT use random twists.

Avoid:

- "It was all a dream."
- "It was a ghost."
- "It was just imagination."
- random prank
- random stranger
- random cat
- unexplained coincidence

Unless the story genuinely builds toward it.

============================================================
8. COMEDY
============================================================

Comedy should come from the situation.

Good comedy:

The protagonist builds an elaborate theory,
only to discover he caused part of the problem himself.

Bad comedy:

Random funny dialogue with no connection to the story.

============================================================
TITLE RULE
============================================================

Titles must create curiosity.

Use different styles.

Examples:

"Nenu Terrace Ki Vellina 10 Minutes Tarvatha..."

"Every Morning Someone Was Moving My Chair"

"Nenu Lock Chesi Vellanu... Mari Idi Ela Jarigindi?"

"Someone Was Using My Terrace"

"Naa Camera Record Chesina Oka Strange Thing"

"Ignored One Small Detail... Then This Happened"

Do NOT end every title with:

"Chudandi"

Do NOT make every title identical.

============================================================
HOOK RULE
============================================================

The first 3–10 seconds must contain a question,
contradiction or unusual event.

BAD:

"Hi guys, welcome back."

GOOD:

"I locked this terrace last night.
Then why is my chair facing the exact place
where I was standing?"

============================================================
8–10 MINUTE VIDEO RULE
============================================================

Long-form ideas must actually contain enough story.

Structure:

ACT 1
Normal situation

ACT 2
First strange event

ACT 3
Investigation

ACT 4
First theory

ACT 5
Theory fails

ACT 6
New clue

ACT 7
Major escalation

ACT 8
Final investigation

ACT 9
Reveal

ACT 10
Payoff

Do NOT take a 30-second idea and stretch it into 10 minutes.

============================================================
SHORTS RULE
============================================================

Shorts should have:

0–3 sec
HOOK

3–10 sec
STRANGE EVENT

10–25 sec
INVESTIGATION

25–45 sec
ESCALATION

45–55 sec
REVEAL

55–60 sec
PAYOFF

============================================================
TELUGU / INDIAN RELATABILITY
============================================================

Naturally use situations such as:

- apartment
- terrace
- neighbours
- courier
- UPI
- WhatsApp
- CCTV
- lift
- staircase
- water tank
- clothes
- bike
- helmet
- keys
- phone
- laptop
- power cut
- inverter
- food delivery
- office call
- online shopping
- morning routine

Do NOT force Indian references.

STORY FIRST.

============================================================
TREND DATA
============================================================

Use current trend data as inspiration.

Do NOT copy trending videos.

Convert trend patterns into original concepts.

INDIA DATA:

{json.dumps(
    india_videos,
    indent=2,
    ensure_ascii=False
)}

INDIA SUMMARY:

{json.dumps(
    india_summary,
    indent=2,
    ensure_ascii=False
)}

WORLDWIDE DATA:

{json.dumps(
    worldwide_videos,
    indent=2,
    ensure_ascii=False
)}

WORLDWIDE SUMMARY:

{json.dumps(
    worldwide_summary,
    indent=2,
    ensure_ascii=False
)}

IMPORTANT:

Worldwide data is represented using the US region
as a broad proxy.

Do not claim it represents every country.

{original_section}

============================================================
INTERNAL IDEA GENERATION
============================================================

Generate MANY candidate ideas internally.

For every candidate:

1. Is the situation relatable?

2. Is the first event specific?

3. Is there a strong question?

4. Does the mystery escalate?

5. Is there a believable false explanation?

6. Are clues planted?

7. Does the reveal explain the clues?

8. Is the ending satisfying?

9. Can one actor shoot it?

10. Does it feel like a real YouTube story?

If the answer is NO to important questions:

DELETE THE IDEA.

Generate another.

Return only the strongest concepts.

============================================================
QUALITY BAR
============================================================

10 strong ideas are better than 50 weak ideas.

Never fill the report just to increase the number.

Every idea must feel:

- interesting
- believable
- visual
- shootable
- suspenseful
- relatable
- logically constructed

============================================================
EVERY IDEA MUST CONTAIN
============================================================

title

genre

logline

hook

setup

mystery_question

escalation

false_explanation

clues

reveal

ending_payoff

content_summary

video_outline

target_audience

estimated_duration

shooting_difficulty

viral_potential

why_viewer_will_continue

why_this_is_not_silly

============================================================
LOGLINE RULE
============================================================

The logline must include:

PROTAGONIST
+
NORMAL SITUATION
+
STRANGE EVENT
+
GOAL
+
OBSTACLE
+
MYSTERY

Bad:

"A man experiences a strange event."

Good:

"While preparing for work, a man notices that someone keeps
moving his terrace chair every morning; convinced somebody is
entering his locked terrace, he secretly records the area,
but the footage creates an even bigger mystery."

============================================================
WHY VIEWER WILL CONTINUE
============================================================

Explain the curiosity chain.

Example:

"First the viewer wants to know who moved the chair.
Then they want to know how the person entered.
Then the recording proves nobody entered.
Finally a small clue reveals what actually happened."

============================================================
WHY THIS IS NOT SILLY
============================================================

Explain why the concept is:

- believable
- relatable
- logically constructed
- not dependent on random coincidence

============================================================
VIRAL POTENTIAL
============================================================

Use only:

HIGH
MEDIUM
LOW

Do not call everything HIGH.

============================================================
OUTPUT FORMAT
============================================================

RETURN ONLY VALID JSON.

No markdown.

No explanation outside JSON.

Use:

{{
  "report_title":
    "YouTube Trend Intelligence Report",

  "executive_goal": {{
    "goal": "",
    "content_direction": "",
    "reason": ""
  }},

  "india_trends": {{
    "overview": "",
    "trending_topics": [],
    "trending_formats": [],
    "trending_genres": [],
    "evidence": []
  }},

  "worldwide_trends": {{
    "overview": "",
    "trending_topics": [],
    "trending_formats": [],
    "trending_genres": [],
    "evidence": []
  }},

  "shorts_trend_ideas": [],

  "long_form_trend_ideas": [],

  "crime_comedy_shorts_trend_based": [],

  "crime_comedy_shorts_normal": [],

  "thriller_comedy_trend_based": [],

  "thriller_comedy_normal": [],

  "monetization_5_months_best_ideas": [],

  "final_best_idea": {{
    "title": "",
    "genre": "",
    "logline": "",
    "hook": "",
    "setup": "",
    "mystery_question": "",
    "escalation": "",
    "false_explanation": "",
    "clues": [],
    "reveal": "",
    "ending_payoff": "",
    "content_summary": "",
    "video_outline": [],
    "target_audience": "",
    "estimated_duration": "",
    "shooting_difficulty": "",
    "viral_potential": "",
    "why_viewer_will_continue": "",
    "why_this_is_not_silly": ""
  }}
}}

Every idea object MUST contain:

title
genre
logline
hook
setup
mystery_question
escalation
false_explanation
clues
reveal
ending_payoff
content_summary
video_outline
target_audience
estimated_duration
shooting_difficulty
viral_potential
why_viewer_will_continue
why_this_is_not_silly

FINAL QUALITY RULE:

If the idea sounds like an AI randomly invented it:

DELETE IT.

If the idea sounds like a normal Telugu/Indian person could
actually experience it and become curious:

KEEP IT.

Generate ORIGINAL ENGAGING STORIES.
"""


    return prompt


# ============================================================
# GEMINI GENERATION
# ============================================================

def generate_report(
    india_videos,
    worldwide_videos,
    original_report
):

    print()
    print(
        "[3/5] Generating engaging YouTube ideas with Gemini..."
    )
    print()

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    prompt = build_prompt(
        india_videos,
        worldwide_videos,
        original_report
    )

    response = client.models.generate_content(

        model="gemini-2.5-flash",

        contents=prompt,

        config=types.GenerateContentConfig(

            response_mime_type="application/json",

            temperature=0.85,

            top_p=0.95,

            top_k=40,

            max_output_tokens=30000
        )
    )

    if not response.text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    text = response.text.strip()

    if text.startswith("```json"):

        text = text[7:]

    elif text.startswith("```"):

        text = text[3:]

    if text.endswith("```"):

        text = text[:-3]

    text = text.strip()

    try:

        report = json.loads(text)

    except json.JSONDecodeError as error:

        print()
        print("=" * 70)
        print("GEMINI JSON ERROR")
        print("=" * 70)
        print()

        print(
            text[:10000]
        )

        print()

        raise RuntimeError(
            f"Gemini JSON parsing failed: {error}"
        )

    required_sections = [

        "shorts_trend_ideas",

        "long_form_trend_ideas",

        "crime_comedy_shorts_trend_based",

        "crime_comedy_shorts_normal",

        "thriller_comedy_trend_based",

        "thriller_comedy_normal",

        "monetization_5_months_best_ideas",

        "final_best_idea"
    ]

    for section in required_sections:

        if section not in report:

            raise RuntimeError(
                f"Gemini response missing section: {section}"
            )

    print()
    print("=" * 70)
    print("ENGAGING IDEA GENERATION COMPLETE")
    print("=" * 70)
    print()

    print(
        "Shorts ideas:",
        len(
            report.get(
                "shorts_trend_ideas",
                []
            )
        )
    )

    print(
        "Long-form ideas:",
        len(
            report.get(
                "long_form_trend_ideas",
                []
            )
        )
    )

    print(
        "Thriller/Comedy ideas:",
        len(
            report.get(
                "thriller_comedy_normal",
                []
            )
        )
    )

    print()

    return report


# ============================================================
# PDF FONT
# ============================================================

def setup_font():

    candidates = [

        Path(
            "C:/Windows/Fonts/NotoSans-Regular.ttf"
        ),

        Path(
            "C:/Windows/Fonts/arial.ttf"
        ),

        Path(
            "C:/Windows/Fonts/calibri.ttf"
        ),
    ]

    for path in candidates:

        if path.exists():

            try:

                pdfmetrics.registerFont(
                    TTFont(
                        "ReportFont",
                        str(path)
                    )
                )

                return "ReportFont"

            except Exception:
                pass

    return "Helvetica"


# ============================================================
# PDF STYLES
# ============================================================

def make_styles(font):

    base = getSampleStyleSheet()

    return {

        "cover": ParagraphStyle(
            "Cover",
            parent=base["Title"],
            fontName=font,
            fontSize=27,
            leading=34,
            alignment=TA_CENTER,
            spaceAfter=15 * mm,
        ),

        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName=font,
            fontSize=11,
            leading=17,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#555555"
            ),
        ),

        "section": ParagraphStyle(
            "Section",
            parent=base["Heading1"],
            fontName=font,
            fontSize=20,
            leading=26,
            spaceBefore=12 * mm,
            spaceAfter=8 * mm,
        ),

        "idea": ParagraphStyle(
            "Idea",
            parent=base["Heading2"],
            fontName=font,
            fontSize=16,
            leading=21,
            spaceBefore=3 * mm,
            spaceAfter=5 * mm,
        ),

        "label": ParagraphStyle(
            "Label",
            parent=base["Normal"],
            fontName=font,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor(
                "#555555"
            ),
            spaceBefore=2 * mm,
            spaceAfter=1 * mm,
        ),

        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9.5,
            leading=15,
            spaceAfter=3 * mm,
        ),

        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9.5,
            leading=14,
            leftIndent=5 * mm,
            firstLineIndent=-3 * mm,
            spaceAfter=1.5 * mm,
        ),
    }


# ============================================================
# PDF SAFE TEXT
# ============================================================

def safe(value):

    if value is None:
        return ""

    return (
        str(value)
        .replace(
            "&",
            "&amp;"
        )
        .replace(
            "<",
            "&lt;"
        )
        .replace(
            ">",
            "&gt;"
        )
    )


# ============================================================
# PDF FIELD
# ============================================================

def add_field(
    story,
    styles,
    label,
    value
):

    if value is None:
        return

    if isinstance(
        value,
        list
    ):

        if not value:
            return

        story.append(
            Paragraph(
                f"<b>{label}</b>",
                styles["label"]
            )
        )

        for item in value:

            story.append(
                Paragraph(
                    f"• {safe(item)}",
                    styles["bullet"]
                )
            )

    else:

        story.append(
            Paragraph(
                f"<b>{label}</b>",
                styles["label"]
            )
        )

        story.append(
            Paragraph(
                safe(value),
                styles["body"]
            )
        )


# ============================================================
# VIRAL BACKGROUND
# ============================================================

def viral_background(value):

    value = str(
        value or ""
    ).upper()

    if value == "HIGH":

        return colors.HexColor(
            "#E8F5E9"
        )

    if value == "MEDIUM":

        return colors.HexColor(
            "#FFF8E1"
        )

    return colors.HexColor(
        "#F5F5F5"
    )


# ============================================================
# IDEA CARD
# ============================================================

def idea_card(
    idea,
    styles
):

    story = []

    title = idea.get(
        "title",
        "Untitled Idea"
    )

    story.append(
        Spacer(
            1,
            5 * mm
        )
    )

    story.append(
        Paragraph(
            safe(title),
            styles["idea"]
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.6,
            color=colors.HexColor(
                "#D5D5D5"
            ),
            spaceBefore=1 * mm,
            spaceAfter=3 * mm,
        )
    )

    add_field(
        story,
        styles,
        "GENRE",
        idea.get("genre")
    )

    add_field(
        story,
        styles,
        "LOGLINE",
        idea.get("logline")
    )

    add_field(
        story,
        styles,
        "HOOK",
        idea.get("hook")
    )

    add_field(
        story,
        styles,
        "SETUP",
        idea.get("setup")
    )

    add_field(
        story,
        styles,
        "MYSTERY QUESTION",
        idea.get("mystery_question")
    )

    add_field(
        story,
        styles,
        "ESCALATION",
        idea.get("escalation")
    )

    add_field(
        story,
        styles,
        "FALSE EXPLANATION",
        idea.get("false_explanation")
    )

    add_field(
        story,
        styles,
        "CLUES",
        idea.get("clues")
    )

    add_field(
        story,
        styles,
        "REVEAL",
        idea.get("reveal")
    )

    add_field(
        story,
        styles,
        "ENDING PAYOFF",
        idea.get("ending_payoff")
    )

    add_field(
        story,
        styles,
        "CONTENT SUMMARY",
        idea.get("content_summary")
    )

    add_field(
        story,
        styles,
        "VIDEO OUTLINE",
        idea.get("video_outline")
    )

    add_field(
        story,
        styles,
        "WHY VIEWER WILL CONTINUE",
        idea.get(
            "why_viewer_will_continue"
        )
    )

    add_field(
        story,
        styles,
        "WHY THIS IS NOT SILLY",
        idea.get(
            "why_this_is_not_silly"
        )
    )

    add_field(
        story,
        styles,
        "TARGET AUDIENCE",
        idea.get("target_audience")
    )

    add_field(
        story,
        styles,
        "ESTIMATED DURATION",
        idea.get("estimated_duration")
    )

    add_field(
        story,
        styles,
        "SHOOTING DIFFICULTY",
        idea.get(
            "shooting_difficulty"
        )
    )

    viral = idea.get(
        "viral_potential",
        ""
    )

    viral_table = Table(
        [[
            Paragraph(
                f"<b>VIRAL POTENTIAL: "
                f"{safe(viral)}</b>",
                styles["body"]
            )
        ]],
        colWidths=[
            165 * mm
        ],
        splitByRow=True,
    )

    viral_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                viral_background(
                    viral
                )
            ),

            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#DDDDDD"
                )
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5 * mm
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5 * mm
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2 * mm
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2 * mm
            ),
        ])
    )

    story.append(
        viral_table
    )

    story.append(
        Spacer(
            1,
            7 * mm
        )
    )

    return story


# ============================================================
# PDF FOOTER
# ============================================================

def footer(
    canvas,
    doc
):

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.setFillColor(
        colors.HexColor(
            "#777777"
        )
    )

    canvas.drawString(
        20 * mm,
        10 * mm,
        "YouTube Trend Intelligence Report"
    )

    canvas.drawRightString(
        190 * mm,
        10 * mm,
        f"Page {doc.page}"
    )

    canvas.restoreState()


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf(
    report,
    output_path
):

    print()
    print(
        "[4/5] Creating professional PDF..."
    )

    font = setup_font()

    styles = make_styles(
        font
    )

    document = SimpleDocTemplate(

        str(output_path),

        pagesize=A4,

        rightMargin=20 * mm,

        leftMargin=20 * mm,

        topMargin=18 * mm,

        bottomMargin=18 * mm,

        title="YouTube Trend Intelligence Report",

        author="YouTube Trend Intelligence Generator",
    )

    story = []

    # ========================================================
    # COVER
    # ========================================================

    story.append(
        Spacer(
            1,
            30 * mm
        )
    )

    story.append(
        Paragraph(
            "YouTube Trend Intelligence Report",
            styles["cover"]
        )
    )

    story.append(
        Paragraph(
            "India + Worldwide YouTube Trends<br/>"
            "Shorts • Long Form • Crime Comedy • Thriller/Comedy",
            styles["subtitle"]
        )
    )

    story.append(
        Spacer(
            1,
            10 * mm
        )
    )

    story.append(
        Paragraph(
            datetime.now().strftime(
                "%d %B %Y"
            ),
            styles["subtitle"]
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # EXECUTIVE
    # ========================================================

    story.append(
        Paragraph(
            "1. CONTENT DIRECTION",
            styles["section"]
        )
    )

    executive = report.get(
        "executive_goal",
        {}
    )

    add_field(
        story,
        styles,
        "GOAL",
        executive.get("goal")
    )

    add_field(
        story,
        styles,
        "CONTENT DIRECTION",
        executive.get(
            "content_direction"
        )
    )

    add_field(
        story,
        styles,
        "REASON",
        executive.get("reason")
    )

    # ========================================================
    # INDIA
    # ========================================================

    story.append(
        Paragraph(
            "2. INDIA — WHAT IS TRENDING",
            styles["section"]
        )
    )

    india = report.get(
        "india_trends",
        {}
    )

    add_field(
        story,
        styles,
        "OVERVIEW",
        india.get("overview")
    )

    add_field(
        story,
        styles,
        "TRENDING TOPICS",
        india.get("trending_topics")
    )

    add_field(
        story,
        styles,
        "TRENDING FORMATS",
        india.get("trending_formats")
    )

    add_field(
        story,
        styles,
        "TRENDING GENRES",
        india.get("trending_genres")
    )

    add_field(
        story,
        styles,
        "EVIDENCE",
        india.get("evidence")
    )

    # ========================================================
    # WORLDWIDE
    # ========================================================

    story.append(
        Paragraph(
            "3. WORLDWIDE — TREND PROXY",
            styles["section"]
        )
    )

    worldwide = report.get(
        "worldwide_trends",
        {}
    )

    add_field(
        story,
        styles,
        "OVERVIEW",
        worldwide.get("overview")
    )

    add_field(
        story,
        styles,
        "TRENDING TOPICS",
        worldwide.get("trending_topics")
    )

    add_field(
        story,
        styles,
        "TRENDING FORMATS",
        worldwide.get("trending_formats")
    )

    add_field(
        story,
        styles,
        "TRENDING GENRES",
        worldwide.get("trending_genres")
    )

    add_field(
        story,
        styles,
        "EVIDENCE",
        worldwide.get("evidence")
    )

    # ========================================================
    # IDEA SECTIONS
    # ========================================================

    sections = [

        (
            "4. SHORTS — TREND BASED",
            "shorts_trend_ideas"
        ),

        (
            "5. LONG-FORM — 8–10 MINUTES",
            "long_form_trend_ideas"
        ),

        (
            "6. CRIME-COMEDY SHORTS — TREND BASED",
            "crime_comedy_shorts_trend_based"
        ),

        (
            "7. CRIME-COMEDY SHORTS — ORIGINAL",
            "crime_comedy_shorts_normal"
        ),

        (
            "8. THRILLER/COMEDY — TREND BASED",
            "thriller_comedy_trend_based"
        ),

        (
            "9. THRILLER/COMEDY — ORIGINAL",
            "thriller_comedy_normal"
        ),
    ]

    for section_title, key in sections:

        story.append(
            Paragraph(
                section_title,
                styles["section"]
            )
        )

        ideas = report.get(
            key,
            []
        )

        for idea in ideas:

            story.extend(
                idea_card(
                    idea,
                    styles
                )
            )

    # ========================================================
    # MONETIZATION
    # ========================================================

    story.append(
        Paragraph(
            "10. BEST IDEAS FOR 5-MONTH GOAL",
            styles["section"]
        )
    )

    best_ideas = report.get(
        "monetization_5_months_best_ideas",
        []
    )

    for idea in best_ideas:

        story.extend(
            idea_card(
                idea,
                styles
            )
        )

    # ========================================================
    # FINAL IDEA
    # ========================================================

    story.append(
        Paragraph(
            "11. FINAL SELECTED IDEA",
            styles["section"]
        )
    )

    final = report.get(
        "final_best_idea",
        {}
    )

    story.extend(
        idea_card(
            final,
            styles
        )
    )

    # ========================================================
    # BUILD
    # ========================================================

    document.build(

        story,

        onFirstPage=footer,

        onLaterPages=footer,
    )

    print()
    print(
        "PDF created successfully:"
    )

    print(
        output_path
    )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(report):

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print(
        "JSON saved:"
    )

    print(
        JSON_FILE
    )


# ============================================================
# RESEND EMAIL
# ============================================================

def send_email(
    pdf_path,
    report
):

    print()
    print(
        "[5/5] Sending PDF through Resend..."
    )

    with open(
        pdf_path,
        "rb"
    ) as file:

        encoded_pdf = base64.b64encode(
            file.read()
        ).decode(
            "utf-8"
        )

    final_title = report.get(
        "final_best_idea",
        {}
    ).get(
        "title",
        "YouTube Trend Intelligence Report"
    )

    payload = {

        "from":
            FROM_EMAIL,

        "to":
            [RECIPIENT_EMAIL],

        "subject":
            "YouTube Trend Intelligence Report - "
            + datetime.now().strftime(
                "%d %B %Y"
            ),

        "html":
            f"""
            <div style="
                font-family:Arial,sans-serif;
                max-width:700px;
                margin:auto;
                color:#222;
            ">

                <h1>
                    YouTube Trend Intelligence Report
                </h1>

                <p>
                    Your latest YouTube Trend Intelligence
                    Report has been generated.
                </p>

                <h2>
                    Final Idea
                </h2>

                <p>
                    <strong>
                        {safe(final_title)}
                    </strong>
                </p>

                <ul>
                    <li>India YouTube trends</li>
                    <li>Worldwide trend proxy</li>
                    <li>Trending genres</li>
                    <li>Engaging Shorts ideas</li>
                    <li>8–10 minute ideas</li>
                    <li>Crime-comedy ideas</li>
                    <li>Thriller/comedy ideas</li>
                    <li>Hooks</li>
                    <li>Mystery questions</li>
                    <li>Escalation</li>
                    <li>Clues</li>
                    <li>Reveals</li>
                    <li>Ending payoffs</li>
                </ul>

                <p>
                    The complete PDF report is attached.
                </p>

            </div>
            """,

        "attachments": [

            {
                "filename":
                    Path(pdf_path).name,

                "content":
                    encoded_pdf,
            }

        ],
    }

    response = requests.post(

        "https://api.resend.com/emails",

        headers={

            "Authorization":
                f"Bearer {RESEND_API_KEY}",

            "Content-Type":
                "application/json",
        },

        json=payload,

        timeout=60,
    )

    if response.status_code >= 400:

        print()
        print(
            "RESEND ERROR:"
        )

        print(
            response.text
        )

        raise RuntimeError(
            f"Resend failed: "
            f"{response.status_code}"
        )

    print()
    print(
        "Email sent successfully."
    )

    print(
        f"Recipient: {RECIPIENT_EMAIL}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    validate_environment()

    # --------------------------------------------------------
    # STEP 1
    # --------------------------------------------------------

    print(
        "[1/5] Connecting to YouTube API..."
    )

    youtube = get_youtube_client()

    print(
        "YouTube API connection successful."
    )

    # --------------------------------------------------------
    # STEP 2
    # --------------------------------------------------------

    print()
    print(
        "[2/5] Fetching current India/World YouTube data..."
    )

    print()
    print(
        "Fetching India..."
    )

    india_videos = fetch_trending_videos(
        youtube,
        "IN",
        50
    )

    print(
        f"India videos received: "
        f"{len(india_videos)}"
    )

    print()
    print(
        "Fetching worldwide proxy..."
    )

    worldwide_videos = fetch_trending_videos(
        youtube,
        "US",
        50
    )

    print(
        "Worldwide proxy uses US region data."
    )

    print(
        f"World proxy videos received: "
        f"{len(worldwide_videos)}"
    )

    print()
    print(
        "Fetching YouTube category names..."
    )

    india_videos = enrich_videos_with_categories(
        youtube,
        india_videos
    )

    worldwide_videos = enrich_videos_with_categories(
        youtube,
        worldwide_videos
    )

    # --------------------------------------------------------
    # PREVIOUS REPORT
    # --------------------------------------------------------

    original_report = load_original_report()

    # --------------------------------------------------------
    # STEP 3
    # --------------------------------------------------------

    report = generate_report(
        india_videos,
        worldwide_videos,
        original_report
    )

    # --------------------------------------------------------
    # STEP 4
    # --------------------------------------------------------

    save_json(
        report
    )

    create_pdf(
        report,
        PDF_FILE
    )

    # --------------------------------------------------------
    # STEP 5
    # --------------------------------------------------------

    send_email(
        PDF_FILE,
        report
    )

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print()

    print(
        f"PDF: {PDF_FILE}"
    )

    print(
        f"JSON: {JSON_FILE}"
    )

    print(
        f"Email: {RECIPIENT_EMAIL}"
    )

    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "Process cancelled by user."
        )

    except Exception as error:

        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print()

        print(
            str(error)
        )

        print()

        sys.exit(1)
