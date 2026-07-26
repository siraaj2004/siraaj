# YouTube Trend Analysis

Automated pipeline that fetches trending YouTube data, generates content ideas, and emails reports on a schedule.

## Features
- Fetches trending video data via the YouTube API (`youtube_agent.py`)
- Generates content ideas from trends (`idea_generator.py`)
- Sends automated email reports (`sender.py`)
- Runs on a schedule (`scheduler.py`)
- CI/CD via GitHub Actions

## Project Structure
├── app.py              # Main entry point
├── config.py            # Configuration settings
├── idea_generator.py    # Generates content ideas from trends
├── scheduler.py         # Handles scheduled runs
├── sender.py             # Sends email reports
├── youtube_agent.py     # Fetches YouTube trending data
├── requirements.txt      # Python dependencies
└── .github/workflows/    # CI/CD pipeline
