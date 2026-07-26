import resend
from config import RESEND_API_KEY, RECIPIENT_EMAIL

resend.api_key = RESEND_API_KEY


def send_email(subject: str, body: str):
    params = {
        "from": "YouTube Trends <onboarding@resend.dev>",
        "to": [RECIPIENT_EMAIL],
        "subject": subject,
        "html": body,
    }

    return resend.Emails.send(params)