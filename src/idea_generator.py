import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_ideas(india_trends, world_trends):
    """
    Generate a professional YouTube Trend Intelligence Report.
    """

    prompt = f"""
Generate a professional YouTube Trend Intelligence Report.

Rules

Do not use Markdown.
Do not use #, ##, ###.
Do not use *, **, -, or bullet symbols.
Use proper section headings.
Leave one blank line between sections.
Number every item.
Write clean professional English.
The report must be suitable for direct PDF export.

==================================================

YOUTUBE TREND INTELLIGENCE REPORT

Date

==================================================

SECTION 1

INDIA YOUTUBE TRENDS

A. Trending YouTube Shorts

Provide the Top 10 trending YouTube Shorts topics.

For every trend include:

Trend Number

Topic

Genre

Why it is Trending

Estimated Views

Target Audience

Best Video Duration

Content Angle

Viral Potential

--------------------------------------------------

B. Trending Long Form Videos (8–10 Minutes)

Provide the Top 10 trending long-form topics.

For every trend include:

Trend Number

Topic

Genre

Why it is Trending

Estimated Views

Target Audience

Recommended Video Length

Content Angle

Viral Potential

==================================================

SECTION 2

WORLD YOUTUBE TRENDS

A. Trending YouTube Shorts

Provide the Top 10 trending YouTube Shorts topics.

For every trend include:

Trend Number

Topic

Genre

Why it is Trending

Estimated Views

Target Audience

Best Video Duration

Content Angle

Viral Potential

--------------------------------------------------

B. Trending Long Form Videos (8–10 Minutes)

Provide the Top 10 trending long-form topics.

For every trend include:

Trend Number

Topic

Genre

Why it is Trending

Estimated Views

Target Audience

Recommended Video Length

Content Angle

Viral Potential

==================================================

SECTION 3

BEST GENRES BASED ON CURRENT TRENDS

Top 20 Shorts Genres

For every genre include:

Genre

Why It Is Trending

Target Audience

Competition

Growth Potential

--------------------------------------------------

Top 20 Long Form Genres

For every genre include:

Genre

Why It Is Trending

Target Audience

Competition

Growth Potential

==================================================

SECTION 4

TREND-BASED YOUTUBE SHORTS IDEAS

Generate 30 Shorts ideas.

For every idea include:

Idea Number

Title

Genre

Hook

Content Summary

Target Audience

Estimated Duration

Viral Potential

==================================================

SECTION 5

TREND-BASED LONG FORM VIDEO IDEAS (8–10 Minutes)

Generate 30 long-form ideas.

For every idea include:

Idea Number

Title

Genre

Video Outline

Target Audience

Estimated Duration

Viral Potential

==================================================

SECTION 6

EVERGREEN SHORTS IDEAS (NOT BASED ON CURRENT TRENDS)

Generate 30 evergreen Shorts ideas.

For every idea include:

Idea Number

Title

Genre

Hook

Content Summary

Target Audience

Estimated Duration

Why It Is Evergreen

==================================================

SECTION 7

EVERGREEN LONG FORM VIDEO IDEAS (8–10 Minutes)

Generate 30 evergreen long-form ideas.

For every idea include:

Idea Number

Title

Genre

Video Outline

Target Audience

Estimated Duration

Why It Is Evergreen

==================================================

SECTION 8

TOP 20 HIGHEST POTENTIAL VIDEO IDEAS

Rank the best 20 ideas from all previous sections.

For every idea include:

Rank

Title

Video Type (Shorts or Long Form)

Genre

Reason It Can Perform Well

Estimated Viral Potential

==================================================

India YouTube Trend Data

{india_trends}

==================================================

World YouTube Trend Data

{world_trends}

Use only the supplied trend data.

Do not use Markdown.

Do not use bullet symbols.

Do not generate tables.

Keep the formatting clean and professional.

Return only the report.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        return response.text.strip()

    except Exception as e:
        return f"Error generating report: {e}"
