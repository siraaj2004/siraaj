import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_ideas(india_trends, world_trends):
    prompt = f"""
Generate a professional YouTube Trend Analysis report.

Rules:

Do not use Markdown.
Do not use #, ##, ###.
Do not use ** or *.
Do not use bullet symbols.
Use proper headings.
Leave one blank line between sections.
Number every trend.
Write clean professional English.
Make the output suitable for exporting directly to a PDF.

Report Structure

YouTube Trend Analysis

Date

India Trends

Trend 1

Topic

Why Trending

Estimated Views

Target Audience

Content Ideas

Trend 2

Topic

Why Trending

Estimated Views

Target Audience

Content Ideas

Trend 3

Topic

Why Trending

Estimated Views

Target Audience

Content Ideas

World Trends

Trend 1

Topic

Why Trending

Estimated Views

Target Audience

Content Ideas

Trend 2

Topic

Why Trending

Estimated Views

Target Audience

Content Ideas

Trend 3

Topic

Why Trending

Estimated Views

Target Audience

Content Ideas

Top 20 YouTube Video Ideas

Number every idea from 1 to 20.

India Trend Data

{india_trends}

World Trend Data

{world_trends}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text
