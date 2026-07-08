import google.generativeai as genai
from config import GEMINI_API_KEY

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Load Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_ideas(trending_titles):
    """
    Generate YouTube content ideas
    based on trending videos.
    """

    try:
        prompt = f"""
        You are a YouTube growth expert.

        Based on these trending videos:

        {trending_titles}

        Generate:
        1. Viral Shorts ideas
        2. Long-form video ideas
        3. Clickable titles
        4. Trending niches

        Keep response simple and clear.
        """

        response = model.generate_content(prompt)

        return response.text

    except Exception as error:
        return f"Error generating ideas: {error}"


# Test run
if __name__ == "__main__":

    sample_titles = [
        "Top AI Tools in 2026",
        "Best YouTube Automation Ideas",
        "How to Grow Fast on YouTube"
    ]

    ideas = generate_ideas(sample_titles)

    print("\nGenerated Ideas:\n")
    print(ideas)
