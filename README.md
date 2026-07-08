# YouTube AI Daily Update Bot

This project automatically collects YouTube trends, analyzes them using Gemini AI, and sends daily updates via email.

## Features

- Automatic daily execution
- Runs even when laptop is OFF (using GitHub Actions)
- Sends updates directly to email
- Gemini AI powered content generation
- YouTube API integration

---

## Project Structure

```text
.github/workflows/main.yml
python_app.py
youtube_agent.py
idea_generator.py
sender.py
schedule.py
config.py
requirements.txt
README.md
```

---

## Installation

Install required packages:

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file:

```env
YOUTUBE_API_KEY=your_youtube_api_key
GEMINI_API_KEY=your_gemini_api_key
EMAIL=your_email
EMAIL_PASSWORD=your_password
```

---

## Run Locally

```bash
python python_app.py
```

---

## GitHub Actions Setup

1. Push project to GitHub
2. Open repository Settings
3. Go to Secrets and Variables → Actions
4. Add:

- YOUTUBE_API_KEY
- GEMINI_API_KEY
- EMAIL
- EMAIL_PASSWORD

GitHub Actions will run automatically based on workflow schedule.

---

## Windows Task Scheduler (Optional)

You can also run automatically using Windows Task Scheduler.

Example:

```bash
python python_app.py
```

---

## Troubleshooting

### Notifications not coming?

Check:

- GitHub Actions workflow status
- Secrets added correctly
- Email credentials valid
- Python script runs without errors
