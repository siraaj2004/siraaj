import resend
from config import RESEND_API_KEY, RECIPIENT_EMAIL

# Configure Resend
resend.api_key = RESEND_API_KEY


def send_email(subject: str, body: str):
    """
    Send an email using Resend.
    """

    try:
        resend.Emails.send({
            "from": "YouTube Trends <onboarding@resend.dev>",
            "to": [RECIPIENT_EMAIL],
            "subject": subject,
            "html": f"""
            <html>
                <body>
                    <pre style="font-family:Arial, sans-serif; white-space:pre-wrap;">
{body}
                    </pre>
                </body>
            </html>
            """
        })

        print("✅ Email sent successfully!")

    except Exception as e:
        print(f"❌ Email sending failed: {e}")
