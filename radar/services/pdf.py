"""PDF report builder — free of Streamlit imports.

Only imports reportlab (optional). Returns raw PDF bytes so the
caller (a Streamlit view) can push it into st.download_button.

Public API:
    build_pdf(title, sections) -> bytes | None
    HAS_PDF -> bool
"""

import io
from datetime import datetime

try:
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    HAS_PDF = True
except ImportError:
    HAS_PDF = False


def build_pdf(title: str, sections: list[dict]) -> bytes | None:
    """Build a PDF report and return its bytes (or None if reportlab absent).

    Each section is a dict with optional keys:
        heading : str
        text    : str
        table   : pandas.DataFrame
    """
    if not HAS_PDF:
        return None
    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Title"],
            textColor=rl_colors.HexColor("#0f172a"),
            fontSize=20,
            spaceAfter=8,
        )
        h2_style = ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            textColor=rl_colors.HexColor("#f6821f"),
            fontSize=14,
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = styles["BodyText"]
        body_style.fontSize = 10
        body_style.textColor = rl_colors.HexColor("#334155")

        story = []
        story.append(Paragraph(title, title_style))
        story.append(
            Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Operator: TELECOM | Mode: LOCAL-ONLY",
                body_style,
            )
        )
        story.append(Spacer(1, 12))

        for s in sections:
            if s.get("heading"):
                story.append(Paragraph(s["heading"], h2_style))
            if s.get("text"):
                story.append(Paragraph(s["text"], body_style))
                story.append(Spacer(1, 6))
            if s.get("table") is not None and len(s["table"]) > 0:
                df = s["table"].head(20)
                data = [list(df.columns)] + df.astype(str).values.tolist()
                t = Table(data, hAlign="LEFT")
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#f6821f")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("GRID", (0, 0), (-1, -1), 0.25, rl_colors.grey),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [rl_colors.white, rl_colors.HexColor("#f8fafc")],
                            ),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("PADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(t)
                story.append(Spacer(1, 12))

        doc.build(story)
        return buf.getvalue()
    except Exception:
        return None
