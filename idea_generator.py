from google import genai


def generate_ideas(client: genai.Client, trending_data: str) -> str:
    prompt = f"""
You are India's best YouTube Trend Analyst and Content Strategist.

Analyze ONLY the YouTube trending data provided below.

==============================
YOUTUBE TRENDING DATA
==============================

{trending_data}

==============================
TASK
==============================

Return ONLY Markdown.

Do NOT write introductions.
Do NOT write conclusions.
Do NOT mention AI.
Do NOT create fake trends.
Use ONLY the supplied trending data for trend-based sections.

Every video idea MUST satisfy:

- Static camera
- One person only
- No second person
- Easy to shoot at home/terrace/room
- Suitable for Indian audience
- Mobile friendly
- Titles MUST be in **bold**

# 1. **YouTube Trend Analysis (India)**

Find the 10 strongest trends from the supplied data.

For every trend write:

## **Trend Name**

**Topic**

**Why it is Trending**
- point
- point
- point

**Creator Opportunity**
- point
- point
- point

---

# 2. **Trending Genres in India**

## **YouTube Shorts Trending Genres**

List every trending Shorts genre found in the supplied data.

Example format

- Genre
- Genre
- Genre

### **Trending Mixed Genres**

Examples

- Thriller + Comedy
- Horror + Comedy
- Motivation + Fitness

Only include combinations that appear in the supplied trends.

---

## **YouTube Long Form (8–10 Minutes) Trending Genres**

List every trending long-form genre.

Format

- Genre
- Genre
- Genre

### **Trending Mixed Genres**

List mixed genres found in long-form trends.

---

# 3. **YouTube Shorts Ideas According to Current Trends**

Generate 10 ideas.

Each idea must follow current trends.

Rules

- Static camera
- One actor
- No second person

For every idea

## **Idea 1**

**Title**

**Hook**

**Content Flow**

- Opening
- Middle
- Ending

**Why It Can Perform Well**

- point
- point
- point

---

# 4. **YouTube Long Form Ideas (8–10 Minutes) According to Current Trends**

Generate 10 ideas.

Rules

- Static camera
- One actor
- No second person

For every idea

## **Idea 1**

**Title**

**Hook**

**Main Points**

- Point
- Point
- Point
- Point
- Point

**Ending**

---

# 5. **Thriller + Comedy YouTube Shorts According to Current Trends**

Generate 10 Shorts ideas.

Rules

- Static camera
- One actor
- No second person

For every idea

## **Idea 1**

**Title**

**Hook**

**Story**

- Beginning
- Conflict
- Twist

**Comedy Moments**

- Point
- Point
- Point

**Thriller Twist**

**Ending**

---

# 6. **Thriller + Comedy Long Form Videos (8–10 Minutes) According to Current Trends**

Generate 10 ideas.

Rules

- Static camera
- One actor
- No second person

For every idea

## **Idea 1**

**Title**

**Hook**

**Story**

- Beginning
- Conflict
- Twist
- Climax
- Ending

**Comedy Moments**

- Point
- Point
- Point

**Thriller Twist**

---

# 7. **Random Thriller + Comedy Shorts (NOT Based on Trends)**

Generate 10 completely original ideas.

Rules

- Static camera
- One actor
- No second person

For every idea

## **Idea 1**

**Title**

**Hook**

**Story**

- Beginning
- Conflict
- Twist

**Comedy Moments**

- Point
- Point
- Point

**Thriller Twist**

**Ending**

---

# 8. **Random Thriller + Comedy Long Form Videos (8–10 Minutes) (NOT Based on Trends)**

Generate 10 completely original ideas.

Rules

- Static camera
- One actor
- No second person

For every idea

## **Idea 1**

**Title**

**Hook**

**Story**

- Beginning
- Conflict
- Twist
- Climax
- Ending

**Comedy Moments**

- Point
- Point
- Point

**Thriller Twist**

==============================
IMPORTANT
==============================

1. Return Markdown ONLY.
2. Every title MUST be **bold**.
3. Keep output clean and mobile friendly.
4. Never repeat ideas.
5. Make every title highly clickable for Indian YouTube.
6. Prefer ideas relatable to Telugu and Indian audiences whenever possible.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text
