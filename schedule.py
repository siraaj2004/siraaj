from apscheduler.schedulers.blocking import BlockingScheduler
from agents.Youtube_agent import get_trending_videos
from agents.idea_generator import generate_ideas
from sender import send_email  # Ensure this function name matches exactly in sender.py

def job():
    try:
        print("Running scheduled task...")

        # Fetch and generate content
        videos = get_trending_videos()
        ideas = generate_ideas(videos)

        # Save ideas locally
        with open("ideas.txt", "w", encoding="utf-8") as f:
            f.write(ideas)

        # Send the email report
        send_email(
            subject="YouTube Trend Report",
            body=ideas
        )

        print("Task completed.")
    except Exception as e:
        print(f"Job failed: {e}")

# Initialize the scheduler
scheduler = BlockingScheduler()

# Schedule the job to run every day at 9:00 AM
scheduler.add_job(job, "cron", hour=9, minute=0, timezone="Asia/Kolkata")

# Start the scheduler (Crucial step missing from your screenshot!)
try:
    print("Scheduler started. Waiting for scheduled jobs...")
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    print("Scheduler stopped.")