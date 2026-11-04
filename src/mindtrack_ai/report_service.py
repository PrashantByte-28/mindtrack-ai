
from datetime import datetime
from io import BytesIO

import pandas as pd
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_mood_pdf_report(
    records: pd.DataFrame,
    report_title: str = "MindTrack AI — Mood Report",
) -> bytes:
    """
    Build a downloadable PDF from the mood records supplied by the app.

    Expected columns:
        date, mood, intensity
    Optional column:
        note

    This function does not access or modify the database.
    """

    required_columns = {"date", "mood", "intensity"}

    if records is None or records.empty:
        raise ValueError("There are no mood records to include in this report.")

    missing_columns = required_columns - set(records.columns)

    if missing_columns:
        raise ValueError(
            "Missing required report columns: "
            + ", ".join(sorted(missing_columns))
        )

    df = records.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["intensity"] = pd.to_numeric(
        df["intensity"], errors="coerce"
    )
    df["mood"] = df["mood"].fillna("Unknown").astype(str)

    df = df.dropna(subset=["date", "intensity"])
    df = df.sort_values("date")

    if df.empty:
        raise ValueError("No valid mood records were found.")

    total_checkins = len(df)
    average_intensity = float(df["intensity"].mean())
    highest_intensity = float(df["intensity"].max())
    lowest_intensity = float(df["intensity"].min())
    unique_days = int(df["date"].dt.date.nunique())
    most_common_mood = str(df["mood"].mode().iloc[0])

    start_date = df["date"].min().strftime("%d %b %Y")
    end_date = df["date"].max().strftime("%d %b %Y")

    mood_counts = (
        df["mood"]
        .value_counts()
        .rename_axis("Mood")
        .reset_index(name="Check-ins")
    )

    daily_summary = (
        df.assign(report_date=df["date"].dt.strftime("%d %b %Y"))
        .groupby("report_date", sort=False)
        .agg(
            Check_ins=("mood", "size"),
            Average_intensity=("intensity", "mean"),
        )
        .reset_index()
    )

    # Create the PDF in memory; no temporary report file is required.
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=report_title,
        author="MindTrack AI",
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#166534"),
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#64748B"),
            fontSize=9,
            leading=13,
            spaceAfter=14,
        )
    )

    story = []

    story.append(Paragraph(report_title, styles["ReportTitle"]))
    story.append(
        Paragraph(
            f"Reporting period: {start_date} to {end_date}<br/>"
            f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
            styles["ReportSubtitle"],
        )
    )

    story.append(Paragraph("Wellness summary", styles["Heading2"]))
    story.append(
        Paragraph(
            "This report summarizes recorded check-ins. "
            "It is intended for personal reflection and is not a "
            "medical assessment or diagnosis.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 10))

    summary_data = [
        ["Metric", "Value"],
        ["Total check-ins", str(total_checkins)],
        ["Days with check-ins", str(unique_days)],
        ["Most recorded mood", most_common_mood],
        ["Average intensity", f"{average_intensity:.2f} / 5"],
        ["Lowest recorded intensity", f"{lowest_intensity:.1f} / 5"],
        ["Highest recorded intensity", f"{highest_intensity:.1f} / 5"],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[85 * mm, 75 * mm],
        repeatRows=1,
    )

    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#166534")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("PADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(summary_table)
    story.append(Spacer(1, 18))

    # Mood distribution chart.
    story.append(Paragraph("Mood distribution", styles["Heading2"]))

    chart = VerticalBarChart()
    chart_data = [mood_counts["Check-ins"].astype(float).tolist()]

    drawing = Drawing(450, 210)
    chart.x = 45
    chart.y = 35
    chart.width = 365
    chart.height = 145
    chart.data = chart_data
    chart.categoryAxis.categoryNames = mood_counts["Mood"].tolist()
    chart.categoryAxis.labels.angle = 25
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(
        1, int(mood_counts["Check-ins"].max())
    ) * 1.15
    chart.valueAxis.valueStep = max(
        1,
        int(mood_counts["Check-ins"].max()) // 5,
    )
    chart.bars[0].fillColor = colors.HexColor("#16A34A")
    chart.barWidth = min(
        28,
        max(8, 300 / max(1, len(mood_counts))),
    )
    chart.groupSpacing = 8

    drawing.add(chart)
    story.append(drawing)
    story.append(Spacer(1, 10))

    # Mood distribution table.
    distribution_data = [["Mood", "Check-ins", "Percentage"]]

    for _, row in mood_counts.iterrows():
        count = int(row["Check-ins"])
        percentage = (count / total_checkins) * 100

        distribution_data.append(
            [str(row["Mood"]), str(count), f"{percentage:.1f}%"]
        )

    distribution_table = Table(
        distribution_data,
        colWidths=[70 * mm, 45 * mm, 45 * mm],
        repeatRows=1,
    )

    distribution_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#166534")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(distribution_table)
    story.append(PageBreak())

    # Daily records table.
    story.append(Paragraph("Daily check-in summary", styles["Heading2"]))

    daily_data = [
        ["Date", "Check-ins", "Avg. intensity"]
    ]

    for _, row in daily_summary.iterrows():
        daily_data.append(
            [
                str(row["report_date"]),
                str(int(row["Check_ins"])),
                f"{float(row['Average_intensity']):.2f} / 5",
            ]
        )

    daily_table = Table(
        daily_data,
        colWidths=[65 * mm, 45 * mm, 50 * mm],
        repeatRows=1,
    )

    daily_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#166534")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F1F5F9"),
                ]),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(daily_table)
    story.append(Spacer(1, 16))

    story.append(
        Paragraph(
            "Privacy note: This PDF may contain personal wellness "
            "information. Store and share it carefully.",
            styles["Italic"],
        )
    )

    document.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
