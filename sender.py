import smtplib
from email.message import EmailMessage
from config import EMAIL_USER, EMAIL_PASSWORD, RECIPIENT_EMAIL


def send_email(subject, body):
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = RECIPIENT_EMAIL
        msg.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.send_message(msg)

        print("✅ Email sent successfully!")

    except Exception as e:
        print(f"❌ Email sending failed: {e}")


if __name__ == "__main__":
    send_email(
        "YouTube Trend Analysis",
        "Your daily YouTube trend report is ready!"
    )