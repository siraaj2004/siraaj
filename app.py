from youtube_agent import get_trending_videos
from idea_generator import generate_ideas
from sender import send_email


def main():
    try:
        print("=" * 60)
        print("YouTube Trend Analysis Workflow Started")
        print("=" * 60)

        # Step 1 - Fetch Trending Videos
        print("\n[1/3] Fetching YouTube trending videos...")

        trends = get_trending_videos(
            region_code="IN",
            max_results=20
        )

        if not trends:
            print("No trending videos found.")
            return

        print(f"Fetched {len(trends)} trending videos.")

        # Step 2 - Generate Report
        print("\n[2/3] Generating trend report...")

        report = generate_ideas(trends)

        if not report:
            print("Failed to generate report.")
            return

        print("Trend report generated successfully.")

        # Step 3 - Send Email
        print("\n[3/3] Sending email...")

        response = send_email(
            subject="YouTube Trend Analysis & Video Ideas",
            body=report
        )

        print("\nEmail sent successfully.")
        print(response)

        print("\nWorkflow completed successfully!")

    except Exception as e:
        print("\nWorkflow failed!")
        print(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()