```python
import os
from dotenv import load_dotenv

from youtube_agent import get_trending_videos
from idea_generator import generate_ideas
from sender import send_email


# Load environment variables
load_dotenv()


def main():
    print("=" * 60)
    print("YouTube Trend Analysis Workflow Started")
    print("=" * 60)

    # Check Gemini API key
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    # Step 1: Fetch YouTube trending videos
    print("\n[1/3] Fetching YouTube trending videos...")

    trending_data = get_trending_videos()

    if not trending_data:
        raise Exception("No trending videos found.")

    print("Fetched YouTube trending videos successfully.")

    # Step 2: Generate trend report
    print("\n[2/3] Generating trend report...")

    report = generate_ideas(trending_data)

    if not report:
        raise Exception("Failed to generate report.")

    print("Trend report generated successfully.")

    # Step 3: Send report via email
    print("\n[3/3] Sending report via email...")

    response = send_email(
        subject="📈 YouTube Trend Analysis Report",
        body=report
    )

    print("Email sent successfully!")
    print(response)

    print("\n" + "=" * 60)
    print("Workflow Completed Successfully")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        print("\nWorkflow Failed!")
        print(f"Error: {e}")
        raise
```
