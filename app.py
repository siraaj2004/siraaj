import smtplib
from email.message import EmailMessage

EMAIL = "munnasiraaj20@gmail.com"
APP_PASSWORD = "bflicpzmqmmunyqy"

msg = EmailMessage()
msg["Subject"] = "Test Email"
msg["From"] = EMAIL
msg["To"] = "munnasiraaj20@gmail.com"
msg.set_content("Hello from Python!")

try:
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()

        smtp.login(EMAIL, APP_PASSWORD)

        smtp.send_message(msg)

    print("Email sent successfully!")

except smtplib.SMTPAuthenticationError as e:
    print("Authentication failed.")
    print(e)

except Exception as e:
    print("Error:", e)
