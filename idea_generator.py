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
You are an expert YouTube Trend Analyst and Content Strategist.

Analyze ONLY the YouTube trending data provided below.

========================
TRENDING DATA
========================

{trending_data}

Return ONLY Markdown.

Use the exact format below.

# **1. YouTube Trend Analysis (India)**

Find the 10 strongest trends from the supplied data.

For each trend use:

## **Trend Name**

**Topic**

**Why It Is Trending**
- Point
- Point
- Point

---

# **2. YouTube Shorts Ideas (Based On Trends)**

Generate 10 YouTube Shorts ideas.

Rules:
- Static camera
- One person only
- No second person
- Easy to shoot at home or terrace
- Based ONLY on supplied trends

For every idea use:

## **Idea Name**

**Title**

**Genre**

**Log Line**

---

# **3. YouTube Long Form Ideas (8–10 Minutes)**

Generate 10 ideas.

Rules:
- 8–10 minutes
- Static camera
- One person only
- No second person
- Based ONLY on supplied trends

For every idea use:

## **Idea Name**

**Title**

**Genre**

**Log Line**

---

# **4. Trending Genres In India**

## **YouTube Shorts Trending Genres**

- Genre
- Genre
- Genre
- Mixed Genre
- Mixed Genre

## **YouTube Long Form Trending Genres (8–10 Minutes)**

- Genre
- Genre
- Genre
- Mixed Genre
- Mixed Genre

---

# **5. Thriller + Comedy YouTube Shorts Ideas (Based On Trends)**

Generate 10 ideas.

Rules:
- Thriller + Comedy mix
- Based ONLY on supplied trends
- Static camera
- One person only
- No second person

For every idea use:

## **Idea Name**

**Title**

**Genre**

**Log Line**

---

# **6. Thriller + Comedy Long Form Ideas (8–10 Minutes) (Based On Trends)**

Generate 10 ideas.

Rules:
- Thriller + Comedy mix
- Based ONLY on supplied trends
- Static camera
- One person only
- No second person
- 8–10 minutes

For every idea use:

## **Idea Name**

**Title**

**Genre**

**Log Line**

---

# **7. Random Thriller + Comedy Shorts Ideas (Not Based On Trends)**

Generate 10 completely original ideas.

Rules:
- Not based on trends
- Thriller + Comedy
- Static camera
- One person only
- No second person

For every idea use:

## **Idea Name**

**Title**

**Genre**

**Log Line**

---

# **8. Random Thriller + Comedy Long Form Ideas (8–10 Minutes) (Not Based On Trends)**

Generate 10 completely original ideas.

Rules:
- Not based on trends
- Thriller + Comedy
- Static camera
- One person only
- No second person
- 8–10 minutes

For every idea use:

## **Idea Name**

**Title**

**Genre**

**Log Line**

---

Requirements:

- Return Markdown only.
- Do not write any introduction.
- Do not write any conclusion.
- Do not use placeholders.
- Every heading must be in bold.
- Every Title must be in bold.
- Keep responses mobile friendly.
- Use ONLY supplied trend data for trend-based sections.
- Random ideas must NOT depend on the trend data.
- The Log Line must be 2–3 sentences that clearly explain the entire video idea without giving a full script.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text
