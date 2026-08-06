import os
from dotenv import load_dotenv

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import darkblue
from reportlab.lib.units import inch

load_dotenv()


def clean_text(text: str) -> str:
    """
    Remove Markdown symbols from AI output.
    """

    replacements = [
        ("###", ""),
        ("##", ""),
        ("#", ""),
        ("**", ""),
        ("*", ""),
        ("```", ""),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text.strip()


def generate_pdf(report_text):

    pdf_name = "Youtube_Trends_Report.pdf"

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER
    title.textColor = darkblue

    heading = styles["Heading2"]

    body = styles["BodyText"]

    doc = SimpleDocTemplate(
        pdf_name,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    story = []

    story.append(
        Paragraph("YouTube Trend Analysis Report", title)
    )

    story.append(Spacer(1, 0.3 * inch))

    report_text = clean_text(report_text)

    for line in report_text.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.endswith(":"):
            story.append(Paragraph(line, heading))

        else:
            story.append(Paragraph(line, body))

    doc.build(story)

    print(f"\nPDF created successfully: {os.path.abspath(pdf_name)}")

    return pdf_name


if __name__ == "__main__":

    print("This file is used by idea_generator.py")
