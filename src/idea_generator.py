import os
import re
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_ideas(india_trends, world_trends):
    """
    Generate a clean, easy-to-read YouTube Trend Intelligence Report.

    The report is formatted with:
    1. Clear section headings
    2. Numbered items
    3. One field per line
    4. Blank lines between items
    5. No Markdown
    6. No bullet symbols
    7. No sample/demo content
    """

    prompt = f"""
Create a professional YouTube Trend Intelligence Report.

IMPORTANT FORMATTING RULES:

The final report must be extremely easy to read.

Do NOT combine multiple items into one paragraph.

Every numbered item MUST be separated by a blank line.

Every field MUST be on its own separate line.

Use this style:

1. Topic: ...
Genre: ...
Why It Is Trending: ...
Estimated Views: ...
Target Audience: ...
Best Video Duration: ...
Content Angle: ...
Viral Potential: ...

2. Topic: ...
Genre: ...
Why It Is Trending: ...
Estimated Views: ...
Target Audience: ...
Best Video Duration: ...
Content Angle: ...
Viral Potential: ...

There MUST be one blank line between item 1 and item 2.

There MUST be one blank line between every numbered item.

Do not use Markdown.

Do not use #.

Do not use ##.

Do not use ###.

Do not use *.

Do not use bullet symbols.

Do not use tables.

Do not put multiple fields on the same line.

Do not create long paragraphs.

Do not repeat information unnecessarily.

Use professional English.

Use clear section headings.

Use numbered lists wherever items are requested.

Return only the report.

==================================================

YOUTUBE TREND INTELLIGENCE REPORT

Date: August 9, 2026

==================================================

SECTION 1

INDIA YOUTUBE TRENDS

A. TRENDING YOUTUBE SHORTS

Generate the Top 10 trending YouTube Shorts topics based ONLY on the supplied India trend data.

For every trend use exactly this structure:

1. Topic: 
Genre: 
Why It Is Trending: 
Estimated Views: 
Target Audience: 
Best Video Duration: 
Content Angle: 
Viral Potential: 

Leave one completely blank line before the next numbered item.

Do this for all 10 trends.

--------------------------------------------------

B. TRENDING LONG FORM VIDEOS

Generate the Top 10 trending long-form YouTube topics.

Recommended video length is 8 to 10 minutes.

For every trend use exactly this structure:

1. Topic: 
Genre: 
Why It Is Trending: 
Estimated Views: 
Target Audience: 
Recommended Video Length: 
Content Angle: 
Viral Potential: 

Leave one completely blank line before the next numbered item.

Do this for all 10 trends.

==================================================

SECTION 2

WORLD YOUTUBE TRENDS

A. TRENDING YOUTUBE SHORTS

Generate the Top 10 trending YouTube Shorts topics based ONLY on the supplied World trend data.

For every trend use exactly this structure:

1. Topic: 
Genre: 
Why It Is Trending: 
Estimated Views: 
Target Audience: 
Best Video Duration: 
Content Angle: 
Viral Potential: 

Leave one completely blank line before the next numbered item.

Do this for all 10 trends.

--------------------------------------------------

B. TRENDING LONG FORM VIDEOS

Generate the Top 10 trending long-form YouTube topics.

Recommended video length is 8 to 10 minutes.

For every trend use exactly this structure:

1. Topic: 
Genre: 
Why It Is Trending: 
Estimated Views: 
Target Audience: 
Recommended Video Length: 
Content Angle: 
Viral Potential: 

Leave one completely blank line before the next numbered item.

Do this for all 10 trends.

==================================================

SECTION 3

BEST YOUTUBE GENRES BASED ON CURRENT TRENDS

A. TOP 20 SHORTS GENRES

Generate 20 genres.

Use exactly this structure:

1. Genre: 
Why It Is Trending: 
Target Audience: 
Competition: 
Growth Potential: 

Leave one completely blank line before the next numbered item.

Do this for all 20 genres.

--------------------------------------------------

B. TOP 20 LONG FORM GENRES

Generate 20 genres.

Use exactly this structure:

1. Genre: 
Why It Is Trending: 
Target Audience: 
Competition: 
Growth Potential: 

Leave one completely blank line before the next numbered item.

Do this for all 20 genres.

==================================================

SECTION 4

TREND BASED YOUTUBE SHORTS IDEAS

Generate 30 Shorts ideas based on the current trends.

Use exactly this structure:

1. Title: 
Genre: 
Hook: 
Content Summary: 
Target Audience: 
Estimated Duration: 
Viral Potential: 

Leave one completely blank line before the next numbered item.

Do this for all 30 ideas.

==================================================

SECTION 5

TREND BASED LONG FORM VIDEO IDEAS

Generate 30 long-form YouTube ideas.

Recommended video length is 8 to 10 minutes.

Use exactly this structure:

1. Title: 
Genre: 
Video Outline: 
Target Audience: 
Estimated Duration: 
Viral Potential: 

Leave one completely blank line before the next numbered item.

Do this for all 30 ideas.

==================================================

SECTION 6

EVERGREEN YOUTUBE SHORTS IDEAS

Generate 30 evergreen Shorts ideas.

These ideas MUST NOT depend on current trends.

Use exactly this structure:

1. Title: 
Genre: 
Hook: 
Content Summary: 
Target Audience: 
Estimated Duration: 
Why It Is Evergreen: 

Leave one completely blank line before the next numbered item.

Do this for all 30 ideas.

==================================================

SECTION 7

EVERGREEN LONG FORM VIDEO IDEAS

Generate 30 evergreen long-form YouTube ideas.

These ideas MUST NOT depend on current trends.

Recommended video length is 8 to 10 minutes.

Use exactly this structure:

1. Title: 
Genre: 
Video Outline: 
Target Audience: 
Estimated Duration: 
Why It Is Evergreen: 

Leave one completely blank line before the next numbered item.

Do this for all 30 ideas.

==================================================

SECTION 8

TOP 20 HIGHEST POTENTIAL VIDEO IDEAS

Rank the best 20 ideas from the previously generated ideas.

Use exactly this structure:

1. Title: 
Video Type: 
Genre: 
Reason It Can Perform Well: 
Estimated Viral Potential: 

Leave one completely blank line before the next numbered item.

Do this for all 20 ideas.

==================================================

INDIA YOUTUBE TREND DATA

{india_trends}

==================================================

WORLD YOUTUBE TREND DATA

{world_trends}

==================================================

FINAL RULES

Use ONLY the supplied trend data for current-trend analysis.

Do not invent external trend data.

Do not add sample content.

Do not add example content.

Do not add explanations before the report.

Do not add explanations after the report.

Do not use Markdown.

Do not use tables.

Do not use bullet points.

Do not merge numbered items.

Do not merge fields.

Keep the report clean and readable.

Return ONLY the completed report.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        if not response or not response.text:
            return "Error: Gemini returned an empty response."

        report = response.text.strip()

        report = clean_report(report)

        return report

    except Exception as e:
        return f"Error generating report: {e}"


def clean_report(report):
    """
    Clean Gemini output and force readable spacing.
    """

    # Remove Markdown heading symbols if Gemini adds them
    report = re.sub(r"(?m)^\s*#{1,6}\s*", "", report)

    # Remove Markdown bullet characters
    report = re.sub(r"(?m)^\s*[\*\•\·]\s*", "", report)

    # Remove repeated horizontal separators
    report = re.sub(r"(?m)^\s*-{3,}\s*$", "", report)
    report = re.sub(r"(?m)^\s*={3,}\s*$", "", report)

    # Remove excessive spaces
    report = re.sub(r"[ \t]+", " ", report)

    # Clean excessive blank lines first
    report = re.sub(r"\n{3,}", "\n\n", report)

    # Make section headings visually separated
    headings = [
        "YOUTUBE TREND INTELLIGENCE REPORT",
        "SECTION 1",
        "SECTION 2",
        "SECTION 3",
        "SECTION 4",
        "SECTION 5",
        "SECTION 6",
        "SECTION 7",
        "SECTION 8",
        "INDIA YOUTUBE TRENDS",
        "WORLD YOUTUBE TRENDS",
        "BEST YOUTUBE GENRES BASED ON CURRENT TRENDS",
        "TREND BASED YOUTUBE SHORTS IDEAS",
        "TREND BASED LONG FORM VIDEO IDEAS",
        "EVERGREEN YOUTUBE SHORTS IDEAS",
        "EVERGREEN LONG FORM VIDEO IDEAS",
        "TOP 20 HIGHEST POTENTIAL VIDEO IDEAS",
        "A. TRENDING YOUTUBE SHORTS",
        "B. TRENDING LONG FORM VIDEOS",
        "A. TOP 20 SHORTS GENRES",
        "B. TOP 20 LONG FORM GENRES"
    ]

    for heading in headings:
        pattern = r"(?m)^\s*" + re.escape(heading) + r"\s*$"
        report = re.sub(
            pattern,
            "\n\n" + heading + "\n",
            report,
            flags=re.IGNORECASE
        )

    # Put every numbered item on a new paragraph.
    # Example:
    # 1. Topic...
    # Genre...
    #
    # 2. Topic...
    # becomes properly separated.
    report = re.sub(
        r"\n\s*(\d+)\.\s+",
        r"\n\n\1. ",
        report
    )

    # Clean blank lines again
    report = re.sub(r"\n{3,}", "\n\n", report)

    # Remove spaces at the beginning/end of lines
    lines = []

    for line in report.splitlines():
        line = line.strip()

        if line:
            lines.append(line)
        else:
            if lines and lines[-1] != "":
                lines.append("")

    report = "\n".join(lines)

    return report.strip()
