import os
import re
import json
import html
import base64
import requests

from datetime import datetime
from dotenv import load_dotenv
from google import genai
from googleapiclient.discovery import build

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
)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")


# ============================================================
# VALIDATE ENVIRONMENT
# ============================================================

required_variables = {
    "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "RESEND_API_KEY": RESEND_API_KEY,
    "FROM_EMAIL": FROM_EMAIL,
    "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
}

missing = [
    name
    for name, value in required_variables.items()
    if not value
]

if missing:
    raise ValueError(
        "Missing variables in .env: "
        + ", ".join(missing)
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# YOUTUBE CLIENT
# ============================================================

youtube = build(
    "youtube",
    "v3",
    developerKey=YOUTUBE_API_KEY
)


# ============================================================
# DATE
# ============================================================

REPORT_DATE = datetime.now().strftime(
    "%B %d, %Y"
)


# ============================================================
# YOUTUBE TREND COLLECTION
# ============================================================

def get_youtube_trends(
    region_code,
    max_results=50
):
    try:

        response = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=max_results
        ).execute()

        trends = []

        for video in response.get("items", []):

            snippet = video.get(
                "snippet",
                {}
            )

            statistics = video.get(
                "statistics",
                {}
            )

            content_details = video.get(
                "contentDetails",
                {}
            )

            trends.append({
                "title": snippet.get(
                    "title",
                    ""
                ),

                "channel": snippet.get(
                    "channelTitle",
                    ""
                ),

                "description": snippet.get(
                    "description",
                    ""
                )[:1000],

                "published_at": snippet.get(
                    "publishedAt",
                    ""
                ),

                "views": statistics.get(
                    "viewCount",
                    "0"
                ),

                "likes": statistics.get(
                    "likeCount",
                    "0"
                ),

                "comments": statistics.get(
                    "commentCount",
                    "0"
                ),

                "duration": content_details.get(
                    "duration",
                    ""
                ),

                "category_id": snippet.get(
                    "categoryId",
                    ""
                ),

                "video_id": video.get(
                    "id",
                    ""
                ),

                "region": region_code
            })

        return trends

    except Exception as e:

        print(
            f"YouTube error [{region_code}]: {e}"
        )

        return []


# ============================================================
# INDIA
# ============================================================

def get_india_trends():

    return get_youtube_trends(
        "IN",
        50
    )


# ============================================================
# WORLD
# ============================================================

def get_world_trends():

    regions = [
        "US",
        "GB",
        "CA",
        "AU",
        "JP"
    ]

    all_trends = []

    for region in regions:

        print(
            f"Collecting trends from {region}..."
        )

        trends = get_youtube_trends(
            region,
            20
        )

        all_trends.extend(trends)

    return all_trends


# ============================================================
# FORMAT DATA
# ============================================================

def format_trend_data(trends):

    output = []

    for index, trend in enumerate(
        trends,
        start=1
    ):

        output.append(
            f"""
TREND {index}

Title: {trend.get("title", "")}
Channel: {trend.get("channel", "")}
Description: {trend.get("description", "")}
Published: {trend.get("published_at", "")}
Views: {trend.get("views", "0")}
Likes: {trend.get("likes", "0")}
Comments: {trend.get("comments", "0")}
Duration: {trend.get("duration", "")}
Category ID: {trend.get("category_id", "")}
Region: {trend.get("region", "")}
"""
        )

    return "\n".join(output)


# ============================================================
# GEMINI GENERATION
# ============================================================

def generate_with_gemini(prompt):

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        if response is None:
            raise RuntimeError(
                "Gemini returned no response."
            )

        text = getattr(
            response,
            "text",
            None
        )

        if not text:
            raise RuntimeError(
                "Gemini returned empty text."
            )

        return text.strip()

    except Exception as e:

        print(
            "Gemini error:",
            e
        )

        raise


# ============================================================
# GENERATE REPORT
# ============================================================

def generate_report(
    india_trends,
    world_trends
):

    india_data = format_trend_data(
        india_trends
    )

    world_data = format_trend_data(
        world_trends
    )

    prompt = f"""
You are a professional YouTube Trend Intelligence
and Content Strategy Analyst.

Create a complete YouTube Trend Intelligence Report.

Report Date:
{REPORT_DATE}

IMPORTANT RULES:

1. Do not invent current YouTube trend data.
2. Use ONLY the supplied YouTube API data when
   explaining current trends.
3. You may create NEW content ideas based on
   patterns found in the data.
4. Clearly separate trend-based ideas from
   evergreen ideas.
5. Do not use markdown tables.
6. Do not use code blocks.
7. Every idea must be separate.
8. Keep the exact requested number of ideas.

==================================================
SECTION 1
INDIA YOUTUBE TRENDS
==================================================

A. TRENDING YOUTUBE SHORTS

Exactly 10.

For each:

1. Topic:
2. Genre:
3. Why It Is Trending:
4. Estimated Views:
5. Target Audience:
6. Best Video Duration:
7. Content Angle:
8. Viral Potential:

B. TRENDING LONG FORM VIDEOS

Exactly 10.

For each:

1. Topic:
2. Genre:
3. Why It Is Trending:
4. Estimated Views:
5. Target Audience:
6. Recommended Video Length:
7. Content Angle:
8. Viral Potential:

==================================================
SECTION 2
WORLD YOUTUBE TRENDS
==================================================

A. TRENDING YOUTUBE SHORTS

Exactly 10.

For each:

1. Topic:
2. Genre:
3. Why It Is Trending:
4. Estimated Views:
5. Target Audience:
6. Best Video Duration:
7. Content Angle:
8. Viral Potential:

B. TRENDING LONG FORM VIDEOS

Exactly 10.

For each:

1. Topic:
2. Genre:
3. Why It Is Trending:
4. Estimated Views:
5. Target Audience:
6. Recommended Video Length:
7. Content Angle:
8. Viral Potential:

==================================================
SECTION 3
BEST YOUTUBE GENRES
==================================================

A. TOP 20 SHORTS GENRES

Exactly 20.

For each:

1. Genre:
2. Why It Is Trending:
3. Target Audience:
4. Competition:
5. Growth Potential:

B. TOP 20 LONG FORM GENRES

Exactly 20.

For each:

1. Genre:
2. Why It Is Trending:
3. Target Audience:
4. Competition:
5. Growth Potential:

==================================================
SECTION 4
TREND BASED YOUTUBE SHORTS IDEAS
==================================================

Exactly 30.

For each:

1. Title:
2. Genre:
3. Hook:
4. Content Summary:
5. Target Audience:
6. Estimated Duration:
7. Viral Potential:

==================================================
SECTION 5
TREND BASED LONG FORM IDEAS
==================================================

Exactly 30.

For each:

1. Title:
2. Genre:
3. Video Outline:
4. Target Audience:
5. Estimated Duration:
6. Viral Potential:

Recommended duration:
8 to 10 minutes.

==================================================
SECTION 6
EVERGREEN YOUTUBE SHORTS IDEAS
==================================================

Exactly 30.

These must NOT depend on current trends.

For each:

1. Title:
2. Genre:
3. Hook:
4. Content Summary:
5. Target Audience:
6. Estimated Duration:
7. Why It Is Evergreen:

==================================================
SECTION 7
EVERGREEN LONG FORM IDEAS
==================================================

Exactly 30.

These must NOT depend on current trends.

For each:

1. Title:
2. Genre:
3. Video Outline:
4. Target Audience:
5. Estimated Duration:
6. Why It Is Evergreen:

Recommended duration:
8 to 10 minutes.

==================================================
SECTION 8
TOP 20 HIGHEST POTENTIAL IDEAS
==================================================

Exactly 20.

IMPORTANT:

Choose ONLY from ideas already generated
in Sections 4, 5, 6 and 7.

Do NOT create new ideas.

For each:

1. Title:
2. Video Type:
3. Genre:
4. Reason It Can Perform Well:
5. Estimated Viral Potential:

==================================================
OUTPUT FORMAT
==================================================

Use plain text.

Do NOT use:

- Markdown headings
- Markdown tables
- Code blocks
- Horizontal lines

Use exactly this structure:

SECTION 1
INDIA YOUTUBE TRENDS

A. TRENDING YOUTUBE SHORTS

1. Topic: Example

Genre: Example

Why It Is Trending:
Example.

Estimated Views:
Example.

Target Audience:
Example.

Best Video Duration:
Example.

Content Angle:
Example.

Viral Potential:
HIGH

2. Topic: Example

...

Keep every idea separate.

==================================================
INDIA YOUTUBE DATA
==================================================

{india_data}

==================================================
WORLD YOUTUBE DATA
==================================================

{world_data}

==================================================

Return ONLY the completed report.
"""

    return generate_with_gemini(
        prompt
    )


# ============================================================
# CLEAN REPORT
# ============================================================

def clean_report(report):

    if not report:
        return ""

    report = report.replace(
        "```text",
        ""
    )

    report = report.replace(
        "```",
        ""
    )

    report = re.sub(
        r"(?m)^\s*#{1,6}\s*",
        "",
        report
    )

    report = re.sub(
        r"\n{4,}",
        "\n\n\n",
        report
    )

    return report.strip()


# ============================================================
# PDF STYLES
# ============================================================

styles = getSampleStyleSheet()


TITLE_STYLE = ParagraphStyle(
    "ReportTitle",
    parent=styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=22,
    leading=28,
    alignment=TA_CENTER,
    spaceAfter=8 * mm
)


SUBTITLE_STYLE = ParagraphStyle(
    "ReportSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=14,
    alignment=TA_CENTER,
    spaceAfter=12 * mm
)


SECTION_STYLE = ParagraphStyle(
    "Section",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=17,
    leading=22,
    spaceBefore=12 * mm,
    spaceAfter=7 * mm
)


SUBSECTION_STYLE = ParagraphStyle(
    "Subsection",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=13,
    leading=18,
    spaceBefore=6 * mm,
    spaceAfter=5 * mm
)


VIDEO_TITLE_STYLE = ParagraphStyle(
    "VideoTitle",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=13,
    leading=17,
    spaceAfter=5 * mm
)


BODY_STYLE = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9.5,
    leading=14,
    spaceAfter=3 * mm
)


# ============================================================
# HTML ESCAPE
# ============================================================

def escape_text(text):

    if text is None:
        return ""

    return html.escape(
        str(text)
    )


def format_body_text(text):

    return escape_text(
        text
    ).replace(
        "\n",
        "<br/>"
    )


# ============================================================
# PDF CARD
# ============================================================

def build_video_card(
    title,
    fields
):

    content = []

    content.append(
        Paragraph(
            escape_text(title),
            VIDEO_TITLE_STYLE
        )
    )

    for label, value in fields:

        if not value:
            continue

        content.append(
            Paragraph(
                f"<b>{escape_text(label)}</b><br/>"
                f"{format_body_text(value)}",
                BODY_STYLE
            )
        )

    table = Table(
        [[content]],
        colWidths=[
            170 * mm
        ]
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor(
                    "#F7F8FA"
                )
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.6,
                colors.HexColor(
                    "#D9DDE3"
                )
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7 * mm
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7 * mm
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6 * mm
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6 * mm
            )
        ])
    )

    return [
        table,
        Spacer(
            1,
            7 * mm
        )
    ]


# ============================================================
# PDF PARSER
# ============================================================

FIELD_NAMES = {
    "Topic",
    "Genre",
    "Why It Is Trending",
    "Estimated Views",
    "Target Audience",
    "Best Video Duration",
    "Recommended Video Length",
    "Content Angle",
    "Viral Potential",
    "Title",
    "Hook",
    "Content Summary",
    "Estimated Duration",
    "Video Outline",
    "Why It Is Evergreen",
    "Video Type",
    "Reason It Can Perform Well",
    "Competition",
    "Growth Potential",
}


def create_pdf(
    report_text,
    output_file
):

    document = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="YouTube Trend Intelligence Report",
        author="YouTube Trend Intelligence"
    )

    story = []

    # --------------------------------------------------------
    # COVER
    # --------------------------------------------------------

    story.append(
        Spacer(
            1,
            30 * mm
        )
    )

    story.append(
        Paragraph(
            "YOUTUBE TREND INTELLIGENCE REPORT",
            TITLE_STYLE
        )
    )

    story.append(
        Paragraph(
            f"Content Strategy & Trend Analysis<br/>"
            f"{escape_text(REPORT_DATE)}",
            SUBTITLE_STYLE
        )
    )

    story.append(
        Paragraph(
            "India + Global YouTube Trend Intelligence",
            BODY_STYLE
        )
    )

    story.append(
        PageBreak()
    )

    lines = [
        line.strip()
        for line in report_text.splitlines()
        if line.strip()
    ]

    current_title = None
    current_fields = []

    def flush_card():

        nonlocal current_title
        nonlocal current_fields

        if current_title:

            story.extend(
                build_video_card(
                    current_title,
                    current_fields
                )
            )

        current_title = None
        current_fields = []

    for line in lines:

        upper = line.upper()

        # ----------------------------------------------------
        # SECTION
        # ----------------------------------------------------

        if re.match(
            r"^SECTION\s+\d+",
            line,
            re.IGNORECASE
        ):

            flush_card()

            story.append(
                Paragraph(
                    escape_text(line),
                    SECTION_STYLE
                )
            )

            continue

        # ----------------------------------------------------
        # SUBSECTION
        # ----------------------------------------------------

        if re.match(
            r"^[A-C]\.\s+",
            line,
            re.IGNORECASE
        ):

            flush_card()

            story.append(
                Paragraph(
                    escape_text(line),
                    SUBSECTION_STYLE
                )
            )

            continue

        # ----------------------------------------------------
        # NUMBERED ITEM
        # ----------------------------------------------------

        numbered = re.match(
            r"^(\d+)\.\s*(.*)$",
            line
        )

        if numbered:

            flush_card()

            text = numbered.group(
                2
            ).strip()

            # "1. Topic: Something"
            field_match = re.match(
                r"^([^:]+):\s*(.*)$",
                text
            )

            if field_match:

                label = field_match.group(
                    1
                ).strip()

                value = field_match.group(
                    2
                ).strip()

                if label in FIELD_NAMES:

                    current_title = value

                else:

                    current_title = text

            else:

                current_title = text

            continue

        # ----------------------------------------------------
        # FIELD
        # ----------------------------------------------------

        field_match = re.match(
            r"^([^:]+):\s*(.*)$",
            line
        )

        if field_match:

            label = field_match.group(
                1
            ).strip()

            value = field_match.group(
                2
            ).strip()

            if label in FIELD_NAMES:

                if label == "Topic":

                    if current_title:
                        current_fields.append(
                            (
                                label,
                                value
                            )
                        )
                    else:
                        current_title = value

                elif label == "Title":

                    if current_title:
                        current_fields.append(
                            (
                                label,
                                value
                            )
                        )
                    else:
                        current_title = value

                else:

                    current_fields.append(
                        (
                            label,
                            value
                        )
                    )

                continue

        # ----------------------------------------------------
        # CONTINUATION
        # ----------------------------------------------------

        if current_fields:

            old_label, old_value = (
                current_fields[-1]
            )

            current_fields[-1] = (
                old_label,
                old_value + " " + line
            )

    flush_card()

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )


# ============================================================
# PAGE NUMBER
# ============================================================

def add_page_number(
    canvas,
    document
):

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.setFillColor(
        colors.HexColor("#777777")
    )

    canvas.drawCentredString(
        A4[0] / 2,
        9 * mm,
        f"Page {document.page}"
    )

    canvas.restoreState()


# ============================================================
# SEND EMAIL USING RESEND HTTP API
# ============================================================

def send_pdf_email(
    pdf_file
):

    print(
        "Sending email through Resend..."
    )

    try:

        with open(
            pdf_file,
            "rb"
        ) as file:

            pdf_bytes = file.read()

        encoded_pdf = base64.b64encode(
            pdf_bytes
        ).decode("utf-8")

        payload = {
            "from": FROM_EMAIL,

            "to": [
                RECIPIENT_EMAIL
            ],

            "subject":
                "YouTube Trend Intelligence Report - "
                + REPORT_DATE,

            "html": f"""
<html>
<body>

<h2>YouTube Trend Intelligence Report</h2>

<p>
Your latest YouTube Trend Intelligence
Report has been generated.
</p>

<p>
Report Date:
{escape_text(REPORT_DATE)}
</p>

<p>
The complete PDF report is attached.
</p>

</body>
</html>
""",

            "attachments": [
                {
                    "filename":
                        os.path.basename(
                            pdf_file
                        ),

                    "content":
                        encoded_pdf
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

        if response.status_code not in (
            200,
            201
        ):

            raise RuntimeError(
                "Resend API error "
                f"{response.status_code}: "
                f"{response.text}"
            )

        print(
            "Email sent successfully."
        )

        print(
            response.json()
        )

    except Exception as e:

        print(
            "Email error:",
            e
        )

        raise


# ============================================================
# SAVE RAW REPORT
# ============================================================

def save_raw_report(
    report,
    filename="youtube_trend_report_raw.txt"
):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report
        )

    print(
        f"Raw report saved: {filename}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=========================================="
    )
    print(
        "YOUTUBE TREND INTELLIGENCE"
    )
    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # INDIA
    # --------------------------------------------------------

    print()
    print(
        "1. Collecting India YouTube trends..."
    )

    india_trends = get_india_trends()

    print(
        f"India trends collected: "
        f"{len(india_trends)}"
    )

    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    print()
    print(
        "2. Collecting global YouTube trends..."
    )

    world_trends = get_world_trends()

    print(
        f"World trends collected: "
        f"{len(world_trends)}"
    )

    if not india_trends:

        raise RuntimeError(
            "No India YouTube trend data found."
        )

    if not world_trends:

        raise RuntimeError(
            "No World YouTube trend data found."
        )

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    print()
    print(
        "3. Generating report with Gemini..."
    )

    report = generate_report(
        india_trends,
        world_trends
    )

    report = clean_report(
        report
    )

    if not report:

        raise RuntimeError(
            "Generated report is empty."
        )

    # --------------------------------------------------------
    # RAW TEXT
    # --------------------------------------------------------

    print()
    print(
        "4. Saving raw report..."
    )

    save_raw_report(
        report
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    pdf_filename = (
        "YouTube_Trend_Intelligence_"
        + datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        + ".pdf"
    )

    print()
    print(
        "5. Creating professional PDF..."
    )

    create_pdf(
        report,
        pdf_filename
    )

    print(
        f"PDF created: {pdf_filename}"
    )

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    print()
    print(
        "6. Sending PDF through Resend..."
    )

    send_pdf_email(
        pdf_filename
    )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    print()
    print(
        "=========================================="
    )

    print(
        "COMPLETED SUCCESSFULLY"
    )

    print(
        f"PDF: {pdf_filename}"
    )

    print(
        "=========================================="
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
