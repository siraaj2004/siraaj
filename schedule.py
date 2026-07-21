import schedule
import time
import subprocess
import sys
from pathlib import Path

# Path to app.py
APP_PATH = Path(__file__).parent / "app.py"


def run_app():
    print("=" * 60)
    print("Running YouTube Trend Agent...")
    print("=" * 60)

    subprocess.run([sys.executable, str(APP_PATH)])


# IST timings
schedule.every().day.at("09:00").do(run_app)
schedule.every().day.at("12:00").do(run_app)
schedule.every().day.at("16:00").do(run_app)
schedule.every().day.at("18:30").do(run_app)

print("Scheduler started...")
print("Scheduled Times:")
print(" • 09:00 AM IST")
print(" • 12:00 PM IST")
print(" • 04:00 PM IST")
print(" • 06:30 PM IST")

while True:
    schedule.run_pending()
    time.sleep(30)
