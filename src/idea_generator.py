YouTube High-CTR Idea Generator
India + Worldwide
Longform + Shorts
Trend-based + Original ideas

Designed for:
- Serious YouTube creators
- High CTR concepts
- Strong hooks
- Strong loglines
- Roman Telugu loglines
- Solo creator production
"""

import os
import json
import re
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ============================================================
# CONFIG
# ============================================================

MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is missing.\n"
        "Add it to your .env file."
    )

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "youtube_high_ctr_ideas.json"
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an elite YouTube content strategist, trend analyst,
story developer and high-CTR idea generator.

Your job is NOT to generate random YouTube ideas.

Your job is to discover and create concepts that make a viewer
think:

"WAIT... WHAT?"
"How is that possible?"
"I NEED TO KNOW WHAT HAPPENS."
"That is actually a crazy idea."
"Why has nobody made this?"

The ideas must have strong curiosity, emotional stakes,
novelty, visual potential and a satisfying payoff.

============================================================
CORE QUALITY RULE
============================================================

NEVER generate silly, childish, generic or filler ideas.

Reject ideas such as:

- random ghost in a kitchen
- missing slipper
- someone hears a sound
- generic prank
- generic challenge
- generic "24 hours" concept
- generic treasure hunt
- generic abandoned house
- generic "I found a mysterious box"
- generic AI experiment with no powerful premise
- generic reaction video
- generic daily vlog
- generic "I tried X"
- concepts that depend only on a cheap twist

A good idea must have a REAL CENTRAL PREMISE.

It should be possible to explain the idea in one powerful sentence.

============================================================
WHAT MAKES A "WAH, WHAT AN IDEA!" CONCEPT
============================================================

Prioritize:

1. A powerful curiosity gap
2. A fresh premise
3. Strong emotional stakes
4. Unexpected contrast
5. A question viewers desperately want answered
6. Visual storytelling
7. Escalation
8. A meaningful reveal/payoff
9. Strong title potential
10. Strong thumbnail potential
11. High retention potential
12. Shareability
13. Cultural relevance where appropriate
14. Feasibility for a solo creator
15. Potential for comments and discussion

The concept should feel like an EVENT,
not merely a topic.

============================================================
CTR PRINCIPLES
============================================================

Titles should create curiosity without lying.

Good title structures include:

- "I Discovered..."
- "Nobody Was Supposed to See..."
- "I Found Out Why..."
- "The Last Person Who..."
- "I Tried to Find..."
- "This Place Has..."
- "Everyone Ignored..."
- "I Followed..."
- "What Happens If..."
- "The Internet Was Wrong About..."
- "I Went Looking For..."
- "I Didn't Expect To Find..."
- "The Truth Behind..."
- "Someone Has Been..."
- "This Shouldn't Exist..."

Do NOT force these structures.
Only use them when they naturally fit.

============================================================
TREND ANALYSIS
============================================================

When trend information is provided, identify:

- rising topics
- emerging formats
- audience curiosity
- creator formats gaining momentum
- cultural moments
- technology trends
- entertainment trends
- social behavior trends
- mystery/investigation trends
- AI trends
- challenge formats
- documentary formats
- storytelling formats
- Shorts formats

Do not simply copy a trend.

Transform the trend into a BETTER ORIGINAL CONCEPT.

Trend = inspiration.

Not copying.

============================================================
INDIA
============================================================

For India ideas consider:

- Telugu
- Hindi
- Tamil
- Kannada
- Malayalam
- Indian internet culture
- Indian cities
- Indian youth
- Indian technology adoption
- Indian cinema
- Indian food culture
- Indian festivals
- Indian transportation
- Indian education
- Indian jobs
- Indian middle-class life
- Indian mysteries
- Indian history
- Indian social behavior
- Indian urban legends
- Indian creator culture

Do not make every idea stereotypically Indian.

============================================================
WORLD
============================================================

For worldwide ideas consider:

- global internet culture
- technology
- AI
- science
- mysteries
- human behavior
- unusual places
- experiments
- documentaries
- history
- future technology
- internet phenomena
- entertainment
- gaming
- creator economy
- unusual real-world events

============================================================
SHORTS
============================================================

Shorts must have a powerful first 1-2 seconds.

Structure:

HOOK
→ curiosity
→ escalation
→ reveal/payoff

Avoid slow setup.

The idea must work within approximately
20-60 seconds.

============================================================
LONGFORM
============================================================

Longform means approximately 8-10 minutes.

Every longform concept should support:

0:00-0:20
POWERFUL HOOK

0:20-1:30
SETUP

1:30-3:00
FIRST DISCOVERY

3:00-5:00
ESCALATION

5:00-7:00
MAJOR COMPLICATION

7:00-8:30
REVEAL / INVESTIGATION

8:30-10:00
PAYOFF

The exact structure can change depending on the concept.

============================================================
ROMAN TELUGU
============================================================

Roman Telugu must sound natural when spoken by a Telugu
YouTube creator.

Do NOT translate word-by-word.

Bad:

"Nenu oka rahasya sthalanni kanugonnanu."

Better conversational style:

"Ee place gurinchi years nunchi oka secret circulate avuthundi.
Kaani dani nijam ento telusukodaniki vellinappudu,
nenu expect chesindhi assalu jaragaledu."

Roman Telugu should sound like natural Telugu speech
typed using English letters.

============================================================
IDEA QUALITY SCORE
============================================================

Score every final idea internally on:

CTR potential
Curiosity
Novelty
Retention
Emotional impact
Visual potential
Shareability
Feasibility

Each score = 1-10.

Only return ideas with:

overall score >= 8.0

Do not show weak ideas merely to fill the list.

If necessary, generate many candidates internally,
reject weak ones,
and return only the strongest.

============================================================
IMPORTANT
============================================================

Do NOT output explanations about your reasoning.

Do NOT output filler.

Do NOT repeat the same concept across sections.

Do NOT use the same hook repeatedly.

Do NOT create fake trends.

If actual trend data is provided, distinguish trend
observations from original ideas.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.
"""


# ============================================================
# USER PROMPT
# ============================================================

USER_PROMPT = """
Create a serious YouTube High-CTR Idea Intelligence Report.

I want the output divided into EXACTLY these 7 sections.

============================================================
1. INDIA YOUTUBE TRENDS
============================================================

Analyze current/recent India YouTube trends.

Separate:

A. India Longform Trends
   Duration: 8-10 minutes

B. India Shorts Trends

For each trend provide:

- trend
- why it is gaining attention
- audience psychology
- content opportunity
- longform potential
- shorts potential
- trend strength (1-10)

Do not invent specific statistics if they are unavailable.

============================================================
2. WORLDWIDE YOUTUBE TRENDS
============================================================

Separate:

A. Worldwide Longform Trends
   Duration: 8-10 minutes

B. Worldwide Shorts Trends

Include:

- trend
- why it is interesting
- audience psychology
- content opportunity
- longform potential
- shorts potential
- trend strength

============================================================
3. YOUTUBE GENRE TRENDS
============================================================

Identify currently strong YouTube genres/formats.

Separate:

A. Longform

B. Shorts

For every genre explain:

- genre
- current opportunity
- why viewers watch it
- what makes it work
- how to make it fresh
- trend strength

============================================================
4. TREND-BASED SHORTS IDEAS
============================================================

Create VERY ENGAGING Shorts ideas based on India + Worldwide
trends.

These must be ORIGINAL concepts inspired by trends,
NOT copies of existing videos.

For every idea return:

- rank
- region
- title
- high_ctr_title
- hook
- logline
- roman_telugu_logline
- concept
- first_2_seconds
- escalation
- ending
- thumbnail_concept
- thumbnail_text
- why_people_will_click
- why_people_will_watch_till_end
- trend_used
- production_difficulty
- estimated_duration
- ctr_score
- retention_score
- novelty_score
- overall_score

Give 10 ideas.

ONLY include ideas that genuinely feel powerful.

============================================================
5. TREND-BASED LONGFORM IDEAS
============================================================

Create VERY ENGAGING 8-10 minute YouTube ideas based on
India + Worldwide trends.

These must be original.

For every idea return:

- rank
- region
- title
- high_ctr_title
- hook
- logline
- roman_telugu_logline
- core_premise
- story_structure
- opening_20_seconds
- escalation
- midpoint
- major_reveal
- ending
- thumbnail_concept
- thumbnail_text
- why_people_will_click
- why_people_will_watch_8_10_minutes
- trend_used
- production_difficulty
- ctr_score
- retention_score
- novelty_score
- overall_score

Give 10 ideas.

============================================================
6. GENERAL NON-TREND SHORTS IDEAS
============================================================

Create ORIGINAL Shorts ideas.

These should NOT depend on current YouTube trends.

They should still feel highly clickable.

Think like:

"What if..."
"Imagine discovering..."
"What would happen if..."
"You realize..."
"Nobody noticed..."
"The one thing..."

But do NOT blindly use those phrases.

Each idea needs:

- rank
- region
- title
- high_ctr_title
- hook
- logline
- roman_telugu_logline
- concept
- first_2_seconds
- escalation
- ending
- thumbnail_concept
- thumbnail_text
- why_people_will_click
- why_people_will_watch_till_end
- production_difficulty
- estimated_duration
- ctr_score
- retention_score
- novelty_score
- overall_score

Give 10 ideas.

============================================================
7. GENERAL NON-TREND LONGFORM IDEAS
============================================================

Create ORIGINAL 8-10 minute concepts.

These must NOT depend on current YouTube trends.

They must have enough story depth for an 8-10 minute video.

For every idea return:

- rank
- region
- title
- high_ctr_title
- hook
- logline
- roman_telugu_logline
- core_premise
- opening_20_seconds
- story_structure
- escalation
- midpoint
- major_reveal
- ending
- thumbnail_concept
- thumbnail_text
- why_people_will_click
- why_people_will_watch_8_10_minutes
- production_difficulty
- ctr_score
- retention_score
- novelty_score
- overall_score

Give 10 ideas.

============================================================
FINAL QUALITY FILTER
============================================================

Before returning the JSON:

Reject any idea that feels:

- silly
- childish
- generic
- predictable
- copied
- weak
- filler
- impossible to make interesting
- dependent only on a twist
- dependent only on "ghost" or "mystery"
- like a basic TikTok/Reel concept

The final ideas should feel like:

"WAH. THIS IS A VIDEO I WOULD CLICK."

At the end include:

TOP_5_OVERALL_IDEAS

Rank the five strongest ideas across all sections.

For each include:

- title
- format
- region
- high_ctr_title
- logline
- roman_telugu_logline
- why_this_is_a_winner

Return ONLY valid JSON.
"""


# ============================================================
# OPENROUTER CALL
# ============================================================

def generate_ideas():
    print("=" * 70)
    print("YOUTUBE HIGH CTR IDEA GENERATOR")
    print("=" * 70)
    print("Generating India + Worldwide ideas...")
    print("Filtering weak/silly concepts...")
    print()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": USER_PROMPT
            }
        ],
        temperature=0.85,
        max_tokens=30000,
    )

    content = response.choices[0].message.content

    return clean_json(content)


# ============================================================
# JSON CLEANER
# ============================================================

def clean_json(text):
    """
    Removes markdown fences if model accidentally returns them.
    """

    text = text.strip()

    # Remove ```json
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove ```
    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    # Find first JSON object
    start = text.find("{")

    # Find final JSON object
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "Model did not return valid JSON."
        )

    json_text = text[start:end + 1]

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print("\nJSON ERROR:")
        print(e)
        print("\nMODEL OUTPUT:")
        print(text[:5000])

        raise

    return data


# ============================================================
# VALIDATION
# ============================================================

def validate_output(data):

    required_sections = [
        "INDIA_YOUTUBE_TRENDS",
        "WORLDWIDE_YOUTUBE_TRENDS",
        "YOUTUBE_GENRE_TRENDS",
        "TREND_BASED_SHORTS_IDEAS",
        "TREND_BASED_LONGFORM_IDEAS",
        "GENERAL_SHORTS_IDEAS",
        "GENERAL_LONGFORM_IDEAS",
        "TOP_5_OVERALL_IDEAS",
    ]

    missing = [
        section
        for section in required_sections
        if section not in data
    ]

    if missing:
        raise ValueError(
            f"Missing sections: {missing}"
        )

    print("✓ All required sections found")

    # Check idea counts
    idea_sections = [
        "TREND_BASED_SHORTS_IDEAS",
        "TREND_BASED_LONGFORM_IDEAS",
        "GENERAL_SHORTS_IDEAS",
        "GENERAL_LONGFORM_IDEAS",
    ]

    for section in idea_sections:

        count = len(data[section])

        print(
            f"✓ {section}: {count} ideas"
        )

        if count < 5:
            print(
                f"WARNING: {section} contains fewer than 5 ideas"
            )


# ============================================================
# SAVE
# ============================================================

def save_output(data):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # Add metadata
    data["_metadata"] = {
        "generated_at": datetime.now().isoformat(),
        "generator": "YouTube High CTR Idea Generator",
        "model": MODEL,
        "version": "2.0",
        "focus": [
            "India",
            "Worldwide",
            "YouTube Trends",
            "Shorts",
            "Longform",
            "High CTR",
            "Roman Telugu"
        ]
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)
    print("SUCCESS")
    print("=" * 70)
    print()
    print(
        f"Saved to: {OUTPUT_FILE}"
    )


# ============================================================
# DISPLAY TOP IDEAS
# ============================================================

def display_top_ideas(data):

    print()
    print("=" * 70)
    print("🔥 TOP 5 HIGH-CTR IDEAS")
    print("=" * 70)

    top = data.get(
        "TOP_5_OVERALL_IDEAS",
        []
    )

    for i, idea in enumerate(top, 1):

        print()
        print(
            f"{i}. {idea.get('title', 'Untitled')}"
        )

        print(
            f"   Format: {idea.get('format', '')}"
        )

        print(
            f"   Region: {idea.get('region', '')}"
        )

        print(
            f"   CTR: {idea.get('high_ctr_title', '')}"
        )

        print(
            f"   Logline: {idea.get('logline', '')}"
        )

        print(
            f"   Roman Telugu: "
            f"{idea.get('roman_telugu_logline', '')}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        data = generate_ideas()

        validate_output(data)

        save_output(data)

        display_top_ideas(data)

        print()
        print(
            f"Full JSON: {OUTPUT_FILE}"
        )

    except Exception as e:

        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)

        print(str(e))

        raise


if __name__ == "__main__":
    main()
