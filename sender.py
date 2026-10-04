import os
import sys
import smtplib
from pathlib import Path
from email.message import EmailMessage


def send_email_with_attachment(
    sender,
    app_password,
    recipient,
    subject,
    body,
    attachment_path
):
    attachment = Path(attachment_path)

    if not attachment.exists():
        raise FileNotFoundError(
            f"Attachment not found: {attachment.resolve()}"
        )

    if not sender:
        raise ValueError("GMAIL_USER is missing")

    if not app_password:
        raise ValueError("GMAIL_APP_PASSWORD is missing")

    if not recipient:
        raise ValueError("GMAIL_TO is missing")

    print("=" * 70)
    print("GMAIL EMAIL SENDING")
    print("=" * 70)

    print(f"From      : {sender}")
    print(f"To        : {recipient}")
    print(f"Subject   : {subject}")
    print(f"Attachment: {attachment}")
    print()

    msg = EmailMessage()

    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.set_content(body)

    with open(attachment, "rb") as f:
        file_data = f.read()

    msg.add_attachment(
        file_data,
        maintype="application",
        subtype="json",
        filename=attachment.name
    )

    print("Connecting to Gmail SMTP...")

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()

        print("Starting TLS...")
        smtp.starttls()

        smtp.ehlo()

        print("Logging into Gmail...")
        smtp.login(sender, app_password)

        print("Sending email...")
        smtp.send_message(msg)

    print()
    print("EMAIL SENT SUCCESSFULLY")
    print("=" * 70)


def main():
    sender = os.environ.get("GMAIL_USER", "").strip()
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    recipient = os.environ.get("GMAIL_TO", "").strip()

    attachment = os.environ.get(
        "YOUTUBE_RESULT_FILE",
        "data/youtube_high_ctr_ideas.json"
    )

    subject = os.environ.get(
        "EMAIL_SUBJECT",
        "YouTube High CTR Ideas"
    )

    body = """Hi Siraaj,

Your YouTube High CTR Idea Generator has completed successfully.

The generated YouTube ideas are attached as:

youtube_high_ctr_ideas.json

The generator collected:
- India YouTube trends
- Worldwide/US proxy trends
- Monetization strategy
- High CTR video ideas

Regards,
YouTube AI Automation
"""

    try:
        send_email_with_attachment(
            sender=sender,
            app_password=app_password,
            recipient=recipient,
            subject=subject,
            body=body,
            attachment_path=attachment
        )

    except Exception as e:
        print()
        print("=" * 70)
        print("EMAIL FAILED")
        print("=" * 70)
        print(f"ERROR: {type(e).__name__}: {e}")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
