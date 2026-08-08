import requests

from config import (
    RESEND_API_KEY,
    FROM_EMAIL,
    RECIPIENT_EMAIL
)


RESEND_URL = "https://api.resend.com/emails"


def send_email(subject, message):

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": FROM_EMAIL,
        "to": [RECIPIENT_EMAIL],
        "subject": subject,
        "html": f"<p>{message}</p>"
    }

    response = requests.post(
        RESEND_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    if response.status_code in (200, 201):
        print("✅ Email sent successfully")
        print(response.json())
        return True

    print("❌ Failed to send email")
    print("Status:", response.status_code)
    print("Response:", response.text)

    return False


if __name__ == "__main__":
    send_email(
        "YouTube Trend Analysis",
        "Your YouTube trend analysis completed successfully."
    )
