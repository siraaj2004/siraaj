import requests
from pathlib import Path

from config import (
    RESEND_API_KEY,
    FROM_EMAIL,
    RECIPIENT_EMAIL
)

RESEND_URL = "https://api.resend.com/emails"


def send_email(subject, message, pdf_path=None):

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}"
    }

    data = {
        "from": FROM_EMAIL,
        "to": RECIPIENT_EMAIL,
        "subject": subject,
        "html": f"<p>{message}</p>"
    }

    files = None

    if pdf_path:
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            return False

        print(f"📎 Attaching PDF: {pdf_path}")

        files = {
            "attachments": (
                pdf_path.name,
                open(pdf_path, "rb"),
                "application/pdf"
            )
        }

    try:
        response = requests.post(
            RESEND_URL,
            headers=headers,
            data=data,
            files=files,
            timeout=60
        )

        print("\nResend response:")
        print("Status:", response.status_code)
        print("Response:", response.text)

        if response.status_code in (200, 201):
            print("✅ Email sent successfully")
            return True

        print("❌ Failed to send email")
        return False

    except Exception as exc:
        print("❌ Email error:", exc)
        return False

    finally:
        if files:
            files["attachments"][1].close()
