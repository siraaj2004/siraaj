from youtube_agent import get_trending_videos
from idea_generator import generate_ideas
from sender import send_email

def main():
    try:
        print("Fetching YouTube trends...")

        trends = get_trending_videos()

        if not trends:
            send_email(
                subject="YouTube Trend Update",
                body="No trending videos found."
            )
            return

        print("Generating ideas...")

        report = generate_ideas(trends)

        send_email(
            subject="🔥 YouTube Trend Report",
            body=report
        )

        print("Trend report sent successfully!")

    except Exception as e:
        print(f"ERROR: {e}")

        send_email(
            subject="YouTube Agent Error",
            body=str(e)
        )

if __name__ == "__main__":
    main()
