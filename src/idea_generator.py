import os
import json
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add GEMINI_API_KEY to your .env file."
    )


MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)


OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


client = genai.Client(api_key=GEMINI_API_KEY)


SYSTEM_INSTRUCTION = """
You are an elite YouTube trend strategist, viral content researcher,
creative director, screenwriter and audience psychology expert.

Your job is NOT to produce random YouTube ideas.

Your job is to identify concepts that make a viewer immediately think:

"WAH... WHAT AN IDEA."

The concepts must have strong curiosity, emotional tension, novelty,
clear audience appeal and a reason to click.

You are generating ideas for an Indian creator who can create:
1. YouTube Shorts
2. YouTube long form videos around 8 to 10 minutes

The creator prefers:
- Thriller
- Mystery
- Suspense
- Psychological concepts
- Unexpected situations
- Real life curiosity
- Technology
- AI
- Internet culture
- Human behaviour
- Indian relatable situations
- Strong twists
- Comedy mixed with serious build up when appropriate
- Concepts that can be filmed with limited resources

Do NOT assume every idea needs expensive production.

VERY IMPORTANT:

Do not generate silly ideas.

Do not generate childish prank concepts.

Do not generate generic "try this challenge" ideas.

Do not generate ordinary reaction videos.

Do not generate generic motivation.

Do not generate generic facts videos.

Do not generate concepts that have already been repeated thousands of times
unless there is a genuinely new angle.

Do not simply change the title of an old idea.

Every idea should contain a strong underlying concept.

The viewer should understand why they need to click.

The first few seconds should create curiosity.

For long form, the concept must have enough story, escalation and payoff
to sustain approximately 8 to 10 minutes.

For Shorts, the concept must have a powerful hook and fast escalation.

Roman Telugu must feel natural and conversational.

Do not translate English word by word.

Use natural Roman Telugu mixed with commonly used English words.

Example style:

"Morning lechi phone open chesthe, ninna night nenu delete chesina
photo malli gallery lo kanipinchindi. Kaani aa photo lo nenu asalu
eppudu vellani place kanipisthundi."

This is only an example of writing style.

Do not copy this example.

Each concept must feel like a real video someone would genuinely want
to watch.

Think like:
MrBeast level curiosity,
Netflix level premise,
Indian audience relatability,
Shorts level hook,
and independent creator practicality.

But do not copy any creator.
"""


USER_REQUIREMENTS = """
Create a complete YouTube Idea Intelligence Report.

The report must contain exactly these seven major sections.

SECTION 1
INDIA YOUTUBE TRENDS

Separate:
A. India YouTube long form trends for 8 to 10 minute videos
B. India YouTube Shorts trends

For each trend explain:
- Trend
- Why it is working
- Audience psychology
- Possible opportunity
- Saturation level
- How a small creator can use it


SECTION 2
WORLD YOUTUBE TRENDS

Separate:
A. World YouTube long form trends for 8 to 10 minute videos
B. World YouTube Shorts trends

For each trend explain:
- Trend
- Why it is working
- Audience psychology
- Opportunity for Indian creators
- Saturation
- Adaptation possibility


SECTION 3
YOUTUBE GENRE TRENDS

Analyze important YouTube genres separately for:
A. Long form 8 to 10 minutes
B. Shorts

Consider genres such as:
- Thriller
- Mystery
- Comedy
- Technology
- AI
- Psychology
- Human behaviour
- Storytelling
- Experiments
- Internet mysteries
- Social experiments
- Documentary style
- Horror
- Finance
- Education
- Lifestyle
- Entertainment

Do not force all genres to be equally important.

Identify the strongest opportunities.


SECTION 4
INDIA AND WORLD TREND BASED SHORTS IDEAS

Generate highly engaging Shorts ideas based specifically on the trends
identified in Sections 1, 2 and 3.

Give 20 ideas.

Every idea must contain:

Idea Number
High CTR Title
Hook
Core Concept
Roman Telugu Logline
Why People Will Click
Why It Can Retain Viewers
Production Difficulty
Trend Used
CTR Score out of 100
Virality Score out of 100
Originality Score out of 100

The Roman Telugu logline must be especially engaging.

It should sound like a movie premise compressed into a Shorts concept.

Avoid silly ideas.


SECTION 5
INDIA AND WORLD TREND BASED LONG FORM IDEAS

Generate 20 highly engaging long form ideas.

Each must work for an 8 to 10 minute video.

Every idea must contain:

Idea Number
High CTR Title
Thumbnail Concept
Opening Hook
Core Premise
Story Structure
Roman Telugu Logline
Escalation
Twist or Payoff
Why People Will Click
Why People Will Watch Until The End
Production Difficulty
Trend Used
CTR Score out of 100
Retention Score out of 100
Originality Score out of 100

The concepts must have enough story to support 8 to 10 minutes.

Avoid simple list videos unless the concept itself is exceptionally strong.


SECTION 6
INDIA AND WORLD GENERAL YOUTUBE IDEAS
NOT BASED ON CURRENT TRENDS
SHORTS

Generate 20 original Shorts ideas.

These must NOT depend on currently trending topics.

Use timeless human curiosity.

Strong areas include:
- Strange situations
- Human psychology
- Mystery
- Everyday life
- Technology
- Relationships
- Fear
- Suspense
- Unexpected consequences
- Social behaviour
- Hidden rules
- Coincidences
- Moral dilemmas

Every idea must contain:

High CTR Title
Hook
Concept
Roman Telugu Logline
Why It Is Interesting
Why It Is Shareable
CTR Score
Originality Score


SECTION 7
INDIA AND WORLD GENERAL YOUTUBE IDEAS
NOT BASED ON CURRENT TRENDS
LONG FORM 8 TO 10 MINUTES

Generate 20 original long form concepts.

These must NOT depend on current trends.

They should have:
- Strong premise
- Escalation
- Mystery or emotional tension
- A payoff
- Enough material for 8 to 10 minutes
- Strong title potential
- Strong thumbnail potential

Every idea must contain:

High CTR Title
Thumbnail Concept
Opening Hook
Core Premise
8 to 10 Minute Story Structure
Roman Telugu Logline
Escalation
Twist or Payoff
Why People Will Click
Why People Will Finish
CTR Score
Retention Score
Originality Score


VERY IMPORTANT FINAL RANKING

At the end create:

TOP 10 HIGHEST CTR IDEAS

Rank the 10 strongest ideas from the entire report.

For each give:

Rank
Title
Format
Roman Telugu Logline
CTR Score
Retention Score
Originality Score
Why This Is A Winner

The first 3 must be exceptional.

Do not fill the report with mediocre ideas just to reach a number.

If an idea is weak, replace it.

QUALITY FILTER

Before returning the final answer, internally score every idea.

Reject an idea if:
- It is generic
- It feels childish
- It feels copied
- It has weak curiosity
- It has no conflict
- It has no escalation
- It has no payoff
- The title is not clickable
- The Roman Telugu logline is boring
- It cannot realistically retain viewers

Only return ideas that survive the quality filter.

Do not mention this internal filtering process in the final report.
"""


TREND_RESEARCH_PROMPT = """
First perform deep current trend analysis using your available knowledge
of YouTube and current internet culture.

Focus on:
India
Global
YouTube Shorts
YouTube long form
Major creator formats
Emerging viewer interests
Fast growing topics
Audience psychology
Content gaps
Oversaturated formats
Underused angles

Important:

Do not invent precise statistics.

If exact current statistics are unavailable, describe the trend
qualitatively instead of making up numbers.

Prioritize recent developments but also distinguish temporary trends
from durable audience behaviour.

Then generate the complete report requested below.

"""


def clean_text(text):
    if not text:
        return ""

    replacements = {
        "#": "",
        "$": "",
        "@": "",
        "*": "",
        "`": "",
        "|": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\n{4,}", "\n\n\n", text)

    return text.strip()


def generate_report():
    prompt = f"""
{TREND_RESEARCH_PROMPT}

{USER_REQUIREMENTS}

IMPORTANT OUTPUT FORMAT

Return a clean professional report.

Do NOT use markdown symbols.

Do NOT use:
#
*
$
@
`
|

You may use:

SECTION 1
SECTION 2
A.
B.
1.
2.
3.

Use plain text headings.

Do not put the entire answer inside JSON.

Do not provide an introduction that wastes space.

Start directly with:

YOUTUBE IDEA INTELLIGENCE REPORT

Date: {datetime.now().strftime("%Y-%m-%d")}

Then generate the full report.
"""

    print()
    print("==============================================")
    print("STARTING YOUTUBE IDEA INTELLIGENCE")
    print("==============================================")
    print()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=1.0,
            max_output_tokens=30000
        )
    )

    if not response or not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return clean_text(response.text)


def save_report(report):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    txt_file = OUTPUT_DIR / f"youtube_idea_report_{timestamp}.txt"
    json_file = OUTPUT_DIR / f"youtube_idea_report_{timestamp}.json"

    txt_file.write_text(
        report,
        encoding="utf-8"
    )

    metadata = {
        "generated_at": datetime.now().isoformat(),
        "model": MODEL_NAME,
        "report_file": str(txt_file),
        "type": "youtube_idea_intelligence"
    }

    json_file.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8"
    )

    return txt_file, json_file


def main():
    try:
        report = generate_report()

        txt_file, json_file = save_report(report)

        print()
        print("==============================================")
        print("IDEA GENERATION COMPLETED")
        print("==============================================")
        print()
        print(f"Report: {txt_file}")
        print(f"Metadata: {json_file}")
        print()

        print(report)

    except Exception as e:
        print()
        print("==============================================")
        print("ERROR")
        print("==============================================")
        print()
        print(str(e))
        raise


if __name__ == "__main__":
    main()
