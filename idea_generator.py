import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)

def generate_ideas(trending_data: str) -> str:
    prompt = f"""
You are an expert YouTube Strategist.

Analyze ONLY the trending data below.

==========================
TRENDING DATA
==========================
{trending_data}

IMPORTANT:
Return ONLY Markdown.

Use proper headings, bold text, numbered lists and bullet points.

DO NOT write huge paragraphs.

Every section must be easy to read on mobile.

# YouTube Trend Analysis

Find the TOP 10 YouTube trends.

For EVERY trend use this format:

## Trend 1

**Topic:**
One line

**Why it is Trending**
- Point 1
- Point 2
- Point 3

**Creator Opportunity**
- Point 1
- Point 2
- Point 3

Repeat for all 10 trends.

# YouTube Shorts Ideas

Generate 10 Shorts ideas.

For every idea use EXACTLY this format.

## Idea 1

**Title**
One line

**Hook**
One sentence.

**Content Flow**
- Opening
- Middle
- Ending

**Why it can go Viral**
- Reason 1
- Reason 2
- Reason 3

Repeat for all ideas.

# Long Form Video Ideas (8-10 Minutes)

Generate 10 ideas.

Use this format.

## Idea 1

**Title**

**Story**

**Hook**

**Main Points**
- Point 1
- Point 2
- Point 3
- Point 4
- Point 5

**Ending**

Repeat.

# Thriller + Comedy Ideas (Telugu Audience)

Generate 10 unique ideas.

Use this format.

## Idea 1

**Title**

**Story**

**Hook**

**Comedy Moments**
- Point 1
- Point 2
- Point 3

**Thriller Twist**

**Ending**

Repeat.

RULES

- Use Markdown.
- All section titles must be H1.
- All idea titles must be H2.
- Make every label bold.
- Use bullet points instead of paragraphs.
- Keep every bullet under 15 words.
- Leave one blank line between sections.
- No giant paragraphs.
- No sample ideas.
- Use only the supplied trending data.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text

if __name__ == "__main__":
    sample_data = """
    Trending Video 1
    Trending Video 2
    Trending Video 3
    """

    result = generate_ideas(sample_data)
    print(result)
