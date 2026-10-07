from __future__ import annotations

import mimetypes
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Missing GitHub Secret: {name}"
        )

    return value


def get_recipients(value: str) -> list[str]:
    recipients = [
        item.strip()
        for item in value.replace(";", ",").split(",")
        if item.strip()
    ]

    if not recipients:
        raise RuntimeError("GMAIL_TO is empty.")

    return recipients


def send_email() -> None:
    gmail_user = required_env("GMAIL_USER")

    # Google App Password, NOT normal Gmail password
    gmail_password = required_env("GMAIL_APP_PASSWORD").replace(" ", "")

    gmail_to = required_env("GMAIL_TO")
    recipients = get_recipients(gmail_to)

    subject = os.getenv(
        "EMAIL_SUBJECT",
        "YouTube High CTR Idea Generator Report"
    )

    output_dir = Path("output")

    attachments = [
        output_dir / "youtube_high_ctr_report.txt",
        output_dir / "youtube_high_ctr_report.json",
    ]

    message = EmailMessage()

    message["From"] = gmail_user
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject

    message.set_content(
        """Hi Siraaj,

Your YouTube High CTR Idea Generator report is ready.

The generated report is attached as:

1. youtube_high_ctr_report.txt
2. youtube_high_ctr_report.json

Important:
If the report says OpenRouter returned 402 Payment Required,
the generator used its offline fallback.

Regards,
YouTube High CTR Idea Generator
"""
    )

    attached_count = 0

    for file_path in attachments:

        if not file_path.exists():
            print(f"[EMAIL] WARNING: File not found: {file_path}")
            continue

        if not file_path.is_file():
            continue

        mime_type, _ = mimetypes.guess_type(file_path.name)

        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype = "application"
            subtype = "octet-stream"

        with file_path.open("rb") as file:
            data = file.read()

        message.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=file_path.name,
        )

        attached_count += 1

        print(
            f"[EMAIL] Attached: {file_path} "
            f"({len(data)} bytes)"
        )

    if attached_count == 0:
        raise RuntimeError(
            "No report files were found in output/."
        )

    print("[EMAIL] Connecting to Gmail SMTP...")

    context = ssl.create_default_context()

    try:

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            context=context,
            timeout=30,
        ) as smtp:

            print("[EMAIL] Logging into Gmail...")

            smtp.login(
                gmail_user,
                gmail_password,
            )

            print("[EMAIL] Sending email...")

            smtp.send_message(message)

    except smtplib.SMTPAuthenticationError as error:

        raise RuntimeError(
            "\n"
            "GMAIL AUTHENTICATION FAILED.\n"
            "\n"
            "Check:\n"
            "1. GMAIL_USER is correct.\n"
            "2. 2-Step Verification is enabled.\n"
            "3. GMAIL_APP_PASSWORD is a Google App Password.\n"
            "4. Do NOT use your normal Gmail password.\n"
        ) from error

    except Exception as error:

        raise RuntimeError(
            f"Gmail sending failed: {type(error).__name__}: {error}"
        ) from error

    print("[EMAIL] =====================================")
    print("[EMAIL] EMAIL SENT SUCCESSFULLY")
    print("[EMAIL] =====================================")


if __name__ == "__main__":

    try:
        send_email()

    except Exception as error:

        print(
            f"[EMAIL] ERROR: {error}",
            file=sys.stderr,
        )

        sys.exit(1)
