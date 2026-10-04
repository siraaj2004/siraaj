import os
import json
import smtplib
import ssl
from pathlib import Path
from email.message import EmailMessage
from email.utils import formataddr


# ============================================================
# CONFIGURATION
# ============================================================

REPORT_FILE = Path("data/youtube_high_ctr_ideas.json")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()


# ============================================================
# VALIDATION
# ============================================================

def check_email_config():

    missing = []

    if not GMAIL_ADDRESS:
        missing.append("GMAIL_ADDRESS")

    if not GMAIL_APP_PASSWORD:
        missing.append("GMAIL_APP_PASSWORD")

    if not RECIPIENT_EMAIL:
        missing.append("RECIPIENT_EMAIL")

    if missing:
        print("=" * 70)
        print("EMAIL CONFIGURATION ERROR")
        print("=" * 70)

        for item in missing:
            print("Missing:", item)

        return False

    return True


# ============================================================
# CREATE EMAIL CONTENT
# ============================================================

def create_email_content(data):

    ideas = data.get("ideas", {})

    best = ideas.get("high_ctr_idea", {})

    shorts = ideas.get("current_shorts", [])

    generated_at = data.get(
        "generated_at",
        "Unknown"
    )

    india_count = data.get(
        "india_trending_count",
        0
    )

    worldwide_count = data.get(
        "worldwide_trending_count",
        0
    )

    subject = (
        "YouTube High CTR Ideas | "
        + best.get(
            "title",
            "New Ideas Generated"
        )
    )

    html = f"""
<html>
<body>

<h2>YouTube High CTR Idea Generator</h2>

<p>
<b>Generated:</b> {generated_at}
</p>

<p>
<b>India trending videos:</b> {india_count}<br>
<b>Worldwide trending videos:</b> {worldwide_count}
</p>

<hr>

<h2>🔥 HIGH CTR IDEA</h2>

<p>
<b>Title:</b><br>
{best.get("title", "")}
</p>

<p>
<b>Genre:</b><br>
{best.get("genre", "")}
</p>

<p>
<b>English Logline:</b><br>
{best.get("english_logline", "")}
</p>

<p>
<b>Roman Telugu Logline:</b><br>
{best.get("roman_telugu_logline", "")}
</p>

<p>
<b>Hook:</b><br>
{best.get("hook", "")}
</p>

<p>
<b>Why This Is Best:</b><br>
{best.get("why_this_is_best", "")}
</p>

<hr>

<h2>🎬 CURRENT YOUTUBE SHORTS</h2>
"""

    for index, idea in enumerate(shorts, start=1):

        html += f"""
<h3>{index}. {idea.get("title", "")}</h3>

<p>
<b>Genre:</b>
{idea.get("genre", "")}
</p>

<p>
<b>English Logline:</b><br>
{idea.get("english_logline", "")}
</p>

<p>
<b>Roman Telugu Logline:</b><br>
{idea.get("roman_telugu_logline", "")}
</p>

<p>
<b>Hook:</b><br>
{idea.get("hook", "")}
</p>

<p>
<b>Content Summary:</b><br>
{idea.get("content_summary", "")}
</p>
"""

    html += """
<hr>

<p>
The complete JSON report is attached to this email.
</p>

<p>
YouTube High CTR Idea Generator
</p>

</body>
</html>
"""

    return subject, html


# ============================================================
# SEND EMAIL
# ============================================================

def send_email():

    print()
    print("=" * 70)
    print("STARTING EMAIL DELIVERY")
    print("=" * 70)

    if not check_email_config():

        raise RuntimeError(
            "Email configuration is incomplete."
        )

    if not REPORT_FILE.exists():

        raise FileNotFoundError(
            f"Report file not found: {REPORT_FILE}"
        )

    print("Report found:", REPORT_FILE)

    # --------------------------------------------------------
    # LOAD JSON
    # --------------------------------------------------------

    try:

        with open(
            REPORT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except Exception as exc:

        raise RuntimeError(
            f"Could not read JSON report: {exc}"
        )

    # --------------------------------------------------------
    # CREATE EMAIL
    # --------------------------------------------------------

    subject, html = create_email_content(data)

    message = EmailMessage()

    message["From"] = formataddr(
        (
            "YouTube High CTR Generator",
            GMAIL_ADDRESS
        )
    )

    message["To"] = RECIPIENT_EMAIL

    message["Subject"] = subject

    message.set_content(
        "Your YouTube High CTR report is ready."
    )

    message.add_alternative(
        html,
        subtype="html"
    )

    # --------------------------------------------------------
    # ATTACH JSON
    # --------------------------------------------------------

    with open(
        REPORT_FILE,
        "rb"
    ) as file:

        file_data = file.read()

    message.add_attachment(
        file_data,
        maintype="application",
        subtype="json",
        filename=REPORT_FILE.name
    )

    # --------------------------------------------------------
    # GMAIL SMTP
    # --------------------------------------------------------

    print("Connecting to Gmail SMTP...")

    context = ssl.create_default_context()

    try:

        with smtplib.SMTP(
            "smtp.gmail.com",
            587,
            timeout=60
        ) as server:

            server.ehlo()

            server.starttls(
                context=context
            )

            server.ehlo()

            print("Logging into Gmail...")

            server.login(
                GMAIL_ADDRESS,
                GMAIL_APP_PASSWORD
            )

            print("Sending email...")

            server.send_message(
                message
            )

        print()
        print("=" * 70)
        print("EMAIL SENT SUCCESSFULLY")
        print("=" * 70)

        print(
            "From:",
            GMAIL_ADDRESS
        )

        print(
            "To:",
            RECIPIENT_EMAIL
        )

        print(
            "Subject:",
            subject
        )

        print("=" * 70)

        return True

    except smtplib.SMTPAuthenticationError as exc:

        print()
        print("=" * 70)
        print("GMAIL AUTHENTICATION FAILED")
        print("=" * 70)

        print(exc)

        print()
        print(
            "Use a Gmail App Password."
        )

        print(
            "Do NOT use your normal Gmail password."
        )

        raise

    except Exception as exc:

        print()
        print("=" * 70)
        print("EMAIL SEND FAILED")
        print("=" * 70)

        print(type(exc).__name__)
        print(str(exc))

        raise


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    send_email()
