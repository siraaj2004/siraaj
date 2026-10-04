import os
import json
import base64
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    HRFlowable,
    Table,
    TableStyle,
)

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-2.5-flash"
).strip()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()

RESEND_FROM = os.getenv(
    "RESEND_FROM",
    "onboarding@resend.dev"
).strip()

RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "reports")

os.makedirs(OUTPUT_DIR, exist_ok=True)

IST = ZoneInfo("Asia/Kolkata")


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

def check_environment():

    required = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
    }

    missing = [
        key
        for key, value in required.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "\nMissing GitHub Secrets / environment variables:\n"
            + "\n".join(f"- {x}" for x in missing)
        )


# ============================================================
# YOUTUBE TREND COLLECTION
# ============================================================

def get_youtube_trends(region_code):

    print(
        f"Collecting YouTube trends for region: {region_code}"
    )

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"YouTube API error for {region_code}: "
            f"{response.status_code}\n"
            f"{response.text[:3000]}"
        )

    data = response.json()

    videos = []

    for item in data.get("items", []):

        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})

        videos.append(
            {
                "id": item.get("id", ""),
                "title": snippet.get("title", ""),
                "channel": snippet.get(
                    "channelTitle",
                    ""
                ),
                "category_id": snippet.get(
                    "categoryId",
                    ""
                ),
                "published_at": snippet.get(
                    "publishedAt",
                    ""
                ),
                "views": int(
                    statistics.get(
                        "viewCount",
                        0
                    ) or 0
                ),
                "likes": int(
                    statistics.get(
                        "likeCount",
                        0
                    ) or 0
                ),
                "comments": int(
                    statistics.get(
                        "commentCount",
                        0
                    ) or 0
                ),
            }
        )

    if not videos:
        raise RuntimeError(
            f"No YouTube trend videos returned for {region_code}"
        )

    return videos


def prepare_trend_data(videos):

    videos = sorted(
        videos,
        key=lambda x: x["views"],
        reverse=True
    )

    return videos[:30]


def trend_text(videos):

    output = []

    for index, video in enumerate(videos, 1):

        output.append(
            f"""
{index}.
TITLE: {video['title']}
CHANNEL: {video['channel']}
VIEWS: {video['views']:,}
LIKES: {video['likes']:,}
COMMENTS: {video['comments']:,}
CATEGORY ID: {video['category_id']}
"""
        )

    return "\n".join(output)


# ============================================================
# OPENROUTER
# ============================================================

def call_openrouter(prompt):

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://github.com/",

        "X-Title":
            "Telugu YouTube High CTR Idea Generator",
    }

    payload = {

        "model": OPENROUTER_MODEL,

        "temperature": 0.9,

        "max_tokens": 16000,

        "messages": [

            {
                "role": "system",

                "content": """
You are an elite YouTube creative director,
screenwriter and CTR strategist.

Your target creator is a Telugu/Indian solo creator.

The creator wants ideas that make people say:

"WAH... WHAT AN IDEA!"

Never give silly, childish, generic or filler
YouTube ideas.

The ideas must have:

- Strong curiosity
- Strong hook
- Clear mystery/problem
- Escalating stakes
- Unexpected reveal
- Emotional or psychological tension
- High retention potential
- High CTR potential
- Indian/Telugu relatability
- Practical solo creator execution
- Simple locations when possible

Preferred genres:

Thriller
Mystery
Crime-Comedy
Dark Comedy
Psychological Thriller
Suspense
Twist
Tech Thriller
Horror-Comedy
High Concept

Avoid:

Lost remote jokes
Wi-Fi jokes
Random ghost jokes
Generic prank videos
Generic motivational videos
Generic challenges
Basic food jokes
Basic misunderstandings
Weak kidnapping jokes
Generic "24 hours" concepts
Copying movie plots
Copying viral videos

Do not make the idea dependent on expensive production.

Do not repeat the same concept.

The final ideas should feel cinematic and original.
"""
            },

            {
                "role": "user",
                "content": prompt
            }

        ]
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=180
    )

    if response.status_code >= 400:

        raise RuntimeError(
            f"""
OpenRouter API ERROR

Status:
{response.status_code}

Response:
{response.text[:5000]}
"""
        )

    data = response.json()

    try:

        content = data[
            "choices"
        ][0][
            "message"
        ][
            "content"
        ]

    except Exception:

        raise RuntimeError(
            "Could not read OpenRouter response:\n"
            + json.dumps(
                data,
                indent=2
            )[:5000]
        )

    return content


# ============================================================
# JSON CLEANING
# ============================================================

def parse_ai_json(text):

    text = text.strip()

    if text.startswith("```json"):

        text = text[
            len("```json"):
        ]

    if text.startswith("```"):

        text = text[
            len("```"):
        ]

    if text.endswith("```"):

        text = text[:-3]

    text = text.strip()

    try:

        return json.loads(text)

    except json.JSONDecodeError:

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:

            try:

                return json.loads(
                    text[start:end + 1]
                )

            except Exception:
                pass

    raise RuntimeError(
        "AI did not return valid JSON.\n\n"
        + text[:5000]
    )


# ============================================================
# AI REPORT GENERATION
# ============================================================

def generate_report(
    india_trends,
    worldwide_trends
):

    date = datetime.now(
        IST
    ).strftime(
        "%d %B %Y"
    )

    india_data = trend_text(
        prepare_trend_data(
            india_trends
        )
    )

    world_data = trend_text(
        prepare_trend_data(
            worldwide_trends
        )
    )

    prompt = f"""

CREATE A PROFESSIONAL YOUTUBE TREND INTELLIGENCE REPORT.

DATE:
{date}

==================================================
CREATOR REQUIREMENTS
==================================================

Creator:

Telugu / Indian
Solo creator
Low production complexity
Strong storytelling

Preferred style:

Thriller
Crime-Comedy
Mystery
Suspense
Dark Comedy
Psychological Thriller
Tech Thriller
Horror-Comedy
High-concept relatable stories

The creator wants ideas that sound like:

"WAH... WHAT A CONCEPT!"

NOT:

"Just another YouTube skit."

==================================================
IMPORTANT
==================================================

Use current YouTube trend data as inspiration.

DO NOT COPY the trending videos.

Transform trend signals into ORIGINAL ideas.

Do not use the same premise repeatedly.

==================================================
ROMAN TELUGU
==================================================

Every idea must have:

English Logline

AND

Roman Telugu Logline

Roman Telugu must sound like natural spoken Telugu
written using English letters.

Example style:

"Ratri intiki vachina oka normal delivery boy,
door open chesi lopaliki vellagane tana order
kosam kaadu, tana life ni marchese oka secret ni
chustadu."

Do not make it a word-for-word translation.

==================================================
HIGH CTR
==================================================

Select ONE strongest idea from the entire report.

Put it at the TOP.

It must have:

Title
Genre
English Logline
Roman Telugu Logline
Hook
Why it has the highest CTR potential

==================================================
SECTION 1
==================================================

1. MONETIZATION GOAL & BEST DIRECTION

Explain:

5 month monetization direction
Content strategy
Shorts strategy
Long-form strategy
CTR strategy
Retention strategy
Upload strategy

==================================================
SECTION 2
==================================================

2. INDIA — WHAT IS TRENDING ON YOUTUBE

Analyze the supplied India trend data.

Include:

Overview
Trending topics
Trending formats
Trending genres
Evidence signals

Do not invent exact trend facts.

==================================================
SECTION 3
==================================================

3. WORLDWIDE — WHAT IS TRENDING ON YOUTUBE

Analyze the supplied worldwide trend data.

IMPORTANT:

The worldwide data is a US YouTube
mostPopular feed proxy.

Clearly say this.

Include:

Overview
Proxy note
Trending topics
Trending formats
Trending genres
Evidence signals

==================================================
SECTION 4
==================================================

4. YOUTUBE SHORTS IDEAS BASED ON CURRENT TRENDS

Create EXACTLY 10 ideas.

These must be:

Very engaging
High curiosity
Original
Trend-inspired
Telugu/Indian
Strong twist
Strong hook

Each idea must contain:

title
genre
english_logline
roman_telugu_logline
hook
content_summary
video_outline
target_audience
estimated_duration
viral_potential
why_it_can_get_high_ctr

==================================================
SECTION 5
==================================================

5. LONG-FORM VIDEO IDEAS — 8–10 MINUTES

Create EXACTLY 8 ideas.

Each must have enough story for 8–10 minutes.

Strong:

Opening
Mystery
Escalation
Midpoint
Climax
Twist/payoff

Each idea must contain the same fields.

==================================================
SECTION 6
==================================================

6. INDIA/WORLD YOUTUBE GENERAL
NOT DIRECTLY BASED ON CURRENT TRENDS
SHORTS

Create EXACTLY 10 evergreen ideas.

These should remain interesting even when current
YouTube trends change.

Each idea must contain the same fields.

==================================================
SECTION 7
==================================================

7. INDIA/WORLD YOUTUBE GENERAL
NOT DIRECTLY BASED ON CURRENT TRENDS
LONG-FORM 8–10 MINUTES

Create EXACTLY 8 evergreen ideas.

Each idea must contain the same fields.

==================================================
QUALITY FILTER
==================================================

Before returning the answer:

Mentally score every idea for:

CTR
Curiosity
Originality
Retention
Telugu relatability
Production feasibility
Ending/payoff

Remove weak ideas.

Never return filler.

==================================================
TREND DATA — INDIA
==================================================

{india_data}

==================================================
TREND DATA — WORLDWIDE PROXY
==================================================

{world_data}

==================================================
RETURN ONLY JSON
==================================================

Use exactly this structure:

{{
    "report_title":
        "YouTube Trend Intelligence Report",

    "report_date":
        "{date}",

    "high_ctr_idea": {{}},

    "section_1_monetization": {{
        "goal": "",
        "best_direction": "",
        "strategy": []
    }},

    "section_2_india_trends": {{
        "overview": "",
        "trending_topics": [],
        "trending_formats": [],
        "trending_genres": [],
        "evidence_signals": []
    }},

    "section_3_worldwide_trends": {{
        "overview": "",
        "proxy_note": "",
        "trending_topics": [],
        "trending_formats": [],
        "trending_genres": [],
        "evidence_signals": []
    }},

    "section_4_current_shorts": [],

    "section_5_current_longform": [],

    "section_6_general_shorts": [],

    "section_7_general_longform": []
}}

"""

    print(
        "Generating high-CTR report..."
    )

    raw = call_openrouter(
        prompt
    )

    return parse_ai_json(
        raw
    )


# ============================================================
# PDF
# ============================================================

def footer(canvas, doc):

    canvas.saveState()

    width, height = A4

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.setFillColor(
        colors.HexColor(
            "#666666"
        )
    )

    canvas.drawString(
        20 * mm,
        10 * mm,
        "YouTube Trend Intelligence Report"
    )

    canvas.drawRightString(
        width - 20 * mm,
        10 * mm,
        f"Page {doc.page}"
    )

    canvas.restoreState()


def build_pdf(
    report,
    india_trends,
    worldwide_trends
):

    timestamp = datetime.now(
        IST
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"YouTube_Trend_Intelligence_"
        f"{timestamp}.pdf"
    )

    pdf_path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    doc = SimpleDocTemplate(

        pdf_path,

        pagesize=A4,

        rightMargin=18 * mm,
        leftMargin=18 * mm,

        topMargin=18 * mm,
        bottomMargin=17 * mm,

        title="YouTube Trend Intelligence Report",

        author="YouTube High CTR Idea Generator"
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=29,
        alignment=TA_CENTER,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceAfter=14
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        spaceBefore=7,
        spaceAfter=10
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        spaceBefore=6,
        spaceAfter=5
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        spaceAfter=6
    )

    story = []

    # --------------------------------------------------------
    # COVER / HIGH CTR
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "YouTube Trend Intelligence Report",
            title_style
        )
    )

    story.append(
        Paragraph(
            "India + Worldwide YouTube Trends",
            subtitle_style
        )
    )

    story.append(
        Paragraph(
            "Shorts • Long Form • High CTR • Thriller • Mystery • Crime-Comedy",
            subtitle_style
        )
    )

    story.append(
        Paragraph(
            report["report_date"],
            subtitle_style
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor(
                "#999999"
            )
        )
    )

    story.append(
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            "HIGH CTR IDEA",
            section_style
        )
    )

    high = report[
        "high_ctr_idea"
    ]

    story.append(
        Paragraph(
            high["title"],
            heading_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Genre:</b> "
            f"{high['genre']}",
            body_style
        )
    )

    story.append(
        Paragraph(
            f"<b>English Logline:</b> "
            f"{high['english_logline']}",
            body_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Roman Telugu Logline:</b> "
            f"{high['roman_telugu_logline']}",
            body_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Hook:</b> "
            f"{high['hook']}",
            body_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Why This Is The Best CTR Choice:</b> "
            f"{high['why_this_is_the_best_ctr_choice']}",
            body_style
        )
    )

    story.append(
        PageBreak()
    )

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    def add_bullets(items):

        for item in items or []:

            story.append(
                Paragraph(
                    f"• {item}",
                    body_style
                )
            )

    def add_idea(
        idea,
        number=None
    ):

        title = idea.get(
            "title",
            "Untitled"
        )

        if number:
            title = f"{number}. {title}"

        story.append(
            Paragraph(
                title,
                heading_style
            )
        )

        fields = [

            (
                "Genre",
                idea.get(
                    "genre",
                    ""
                )
            ),

            (
                "English Logline",
                idea.get(
                    "english_logline",
                    ""
                )
            ),

            (
                "Roman Telugu Logline",
                idea.get(
                    "roman_telugu_logline",
                    ""
                )
            ),

            (
                "Hook",
                idea.get(
                    "hook",
                    ""
                )
            ),

            (
                "Content Summary",
                idea.get(
                    "content_summary",
                    ""
                )
            ),

            (
                "Target Audience",
                idea.get(
                    "target_audience",
                    ""
                )
            ),

            (
                "Estimated Duration",
                idea.get(
                    "estimated_duration",
                    ""
                )
            ),

            (
                "Viral Potential",
                idea.get(
                    "viral_potential",
                    ""
                )
            ),

            (
                "Why It Can Get High CTR",
                idea.get(
                    "why_it_can_get_high_ctr",
                    ""
                )
            ),
        ]

        for label, value in fields:

            story.append(
                Paragraph(
                    f"<b>{label}:</b> {value}",
                    body_style
                )
            )

        story.append(
            Paragraph(
                "<b>Video Outline:</b>",
                body_style
            )
        )

        for step in idea.get(
            "video_outline",
            []
        ):

            story.append(
                Paragraph(
                    f"• {step}",
                    body_style
                )
            )

        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor(
                    "#CCCCCC"
                ),
                spaceBefore=3,
                spaceAfter=9
            )
        )

    # --------------------------------------------------------
    # SECTION 1
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "1. MONETIZATION GOAL & BEST DIRECTION",
            section_style
        )
    )

    monetization = report[
        "section_1_monetization"
    ]

    story.append(
        Paragraph(
            f"<b>Goal:</b> "
            f"{monetization['goal']}",
            body_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Best Direction:</b> "
            f"{monetization['best_direction']}",
            body_style
        )
    )

    story.append(
        Paragraph(
            "Strategy",
            heading_style
        )
    )

    add_bullets(
        monetization.get(
            "strategy",
            []
        )
    )

    # --------------------------------------------------------
    # SECTION 2
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "2. INDIA — WHAT IS TRENDING ON YOUTUBE",
            section_style
        )
    )

    india = report[
        "section_2_india_trends"
    ]

    story.append(
        Paragraph(
            india["overview"],
            body_style
        )
    )

    for label, key in [
        (
            "Trending Topics",
            "trending_topics"
        ),
        (
            "Trending Formats",
            "trending_formats"
        ),
        (
            "Trending Genres",
            "trending_genres"
        ),
        (
            "Evidence Signals",
            "evidence_signals"
        )
    ]:

        story.append(
            Paragraph(
                label,
                heading_style
            )
        )

        add_bullets(
            india.get(
                key,
                []
            )
        )

    story.append(
        PageBreak()
    )

    # --------------------------------------------------------
    # SECTION 3
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "3. WORLDWIDE — WHAT IS TRENDING ON YOUTUBE",
            section_style
        )
    )

    world = report[
        "section_3_worldwide_trends"
    ]

    story.append(
        Paragraph(
            world["overview"],
            body_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Proxy Note:</b> "
            f"{world['proxy_note']}",
            body_style
        )
    )

    for label, key in [
        (
            "Trending Topics",
            "trending_topics"
        ),
        (
            "Trending Formats",
            "trending_formats"
        ),
        (
            "Trending Genres",
            "trending_genres"
        ),
        (
            "Evidence Signals",
            "evidence_signals"
        )
    ]:

        story.append(
            Paragraph(
                label,
                heading_style
            )
        )

        add_bullets(
            world.get(
                key,
                []
            )
        )

    # --------------------------------------------------------
    # SECTION 4
    # --------------------------------------------------------

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "4. YOUTUBE SHORTS IDEAS BASED ON CURRENT TRENDS",
            section_style
        )
    )

    for i, idea in enumerate(
        report["section_4_current_shorts"],
        1
    ):

        add_idea(
            idea,
            i
        )

    # --------------------------------------------------------
    # SECTION 5
    # --------------------------------------------------------

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "5. LONG-FORM VIDEO IDEAS — 8–10 MINUTES",
            section_style
        )
    )

    for i, idea in enumerate(
        report["section_5_current_longform"],
        1
    ):

        add_idea(
            idea,
            i
        )

    # --------------------------------------------------------
    # SECTION 6
    # --------------------------------------------------------

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "6. INDIA/WORLD YOUTUBE GENERAL — "
            "NOT DIRECTLY BASED ON CURRENT TRENDS — SHORTS",
            section_style
        )
    )

    for i, idea in enumerate(
        report["section_6_general_shorts"],
        1
    ):

        add_idea(
            idea,
            i
        )

    # --------------------------------------------------------
    # SECTION 7
    # --------------------------------------------------------

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "7. INDIA/WORLD YOUTUBE GENERAL — "
            "NOT DIRECTLY BASED ON CURRENT TRENDS — "
            "LONG-FORM 8–10 MINUTES",
            section_style
        )
    )

    for i, idea in enumerate(
        report["section_7_general_longform"],
        1
    ):

        add_idea(
            idea,
            i
        )

    # --------------------------------------------------------
    # DATA SUMMARY
    # --------------------------------------------------------

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "TREND DATA USED",
            section_style
        )
    )

    story.append(
        Paragraph(
            "India uses the YouTube mostPopular feed with "
            "regionCode=IN. Worldwide is represented by "
            "the US mostPopular feed as a proxy.",
            body_style
        )
    )

    rows = [
        [
            "Region",
            "Videos",
            "Top Video"
        ]
    ]

    for region, videos in [
        (
            "India",
            india_trends
        ),
        (
            "Worldwide Proxy (US)",
            worldwide_trends
        )
    ]:

        top = max(
            videos,
            key=lambda x: x["views"]
        )

        rows.append(
            [
                region,
                str(len(videos)),
                top["title"][:75]
            ]
        )

    table = Table(
        rows,
        colWidths=[
            45 * mm,
            25 * mm,
            105 * mm
        ]
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#EEEEEE"
                    )
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#BBBBBB"
                    )
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                ),
            ]
        )
    )

    story.append(
        table
    )

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer
    )

    return pdf_path


# ============================================================
# RESEND EMAIL
# ============================================================

def send_email(
    pdf_path,
    report
):

    subject = (
        "YouTube Trend Intelligence Report | "
        + report[
            "high_ctr_idea"
        ][
            "title"
        ]
    )

    with open(
        pdf_path,
        "rb"
    ) as file:

        pdf_base64 = base64.b64encode(
            file.read()
        ).decode(
            "utf-8"
        )

    high = report[
        "high_ctr_idea"
    ]

    html = f"""
<!DOCTYPE html>

<html>

<body
style="
font-family:Arial,sans-serif;
line-height:1.6;
">

<h1>
YouTube Trend Intelligence Report
</h1>

<p>
Your latest YouTube Trend Intelligence Report
has been generated successfully.
</p>

<h2>
HIGH CTR IDEA
</h2>

<h3>
{high["title"]}
</h3>

<p>
<b>Genre:</b>
{high["genre"]}
</p>

<p>
<b>English Logline:</b>
{high["english_logline"]}
</p>

<p>
<b>Roman Telugu Logline:</b>
{high["roman_telugu_logline"]}
</p>

<p>
<b>Hook:</b>
{high["hook"]}
</p>

<p>
<b>Why this is the best CTR choice:</b>
{high["why_this_is_the_best_ctr_choice"]}
</p>

<hr>

<h2>
Complete PDF Attached
</h2>

<ul>

<li>
Monetization Goal & Best Direction
</li>

<li>
India YouTube Trends
</li>

<li>
Worldwide YouTube Trends
</li>

<li>
Current Trend Shorts
</li>

<li>
Current Trend Long Form
</li>

<li>
Evergreen Shorts
</li>

<li>
Evergreen Long Form
</li>

</ul>

</body>

</html>
"""

    payload = {

        "from":
            RESEND_FROM,

        "to":
            [RECIPIENT_EMAIL],

        "subject":
            subject,

        "html":
            html,

        "attachments":
            [
                {
                    "filename":
                        os.path.basename(
                            pdf_path
                        ),

                    "content":
                        pdf_base64
                }
            ]
    }

    response = requests.post(

        "https://api.resend.com/emails",

        headers={
            "Authorization":
                f"Bearer {RESEND_API_KEY}",

            "Content-Type":
                "application/json"
        },

        json=payload,

        timeout=60
    )

    if response.status_code >= 400:

        raise RuntimeError(
            f"""
RESEND ERROR

Status:
{response.status_code}

Response:
{response.text}
"""
        )

    result = response.json()

    print(
        "Resend email ID:",
        result.get(
            "id",
            "unknown"
        )
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("STARTING YOUTUBE HIGH CTR IDEA GENERATOR")
    print("=" * 70)
    print()

    check_environment()

    # --------------------------------------------------------
    # INDIA
    # --------------------------------------------------------

    print(
        "[1/5] Collecting India trends..."
    )

    india_trends = get_youtube_trends(
        "IN"
    )

    print(
        f"India videos collected: "
        f"{len(india_trends)}"
    )

    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    print(
        "[2/5] Collecting worldwide proxy trends..."
    )

    worldwide_trends = get_youtube_trends(
        "US"
    )

    print(
        f"Worldwide proxy videos collected: "
        f"{len(worldwide_trends)}"
    )

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    print(
        "[3/5] Generating high-CTR ideas..."
    )

    report = generate_report(
        india_trends,
        worldwide_trends
    )

    print(
        "High CTR idea:",
        report[
            "high_ctr_idea"
        ][
            "title"
        ]
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    print(
        "[4/5] Creating professional PDF..."
    )

    pdf_path = build_pdf(
        report,
        india_trends,
        worldwide_trends
    )

    print(
        "PDF created:",
        pdf_path
    )

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    print(
        "[5/5] Sending PDF through Resend..."
    )

    send_email(
        pdf_path,
        report
    )

    print()
    print("=" * 70)
    print("SUCCESS")
    print("=" * 70)
    print()
    print(
        "Report:",
        pdf_path
    )
    print()


if __name__ == "__main__":
    main()
