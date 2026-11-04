
# src/mindtrack_ai/insights_service.py

from __future__ import annotations

from collections import Counter

import pandas as pd

from mindtrack_ai.llm_service import generate_response


def build_mood_summary(records: pd.DataFrame) -> dict:
    """Create a privacy-conscious summary from saved mood records."""

    required = {"date", "mood", "intensity"}
    missing = required.difference(records.columns)

    if missing:
        raise ValueError(
            "Mood records are missing required columns: "
            + ", ".join(sorted(missing))
        )

    if records.empty:
        raise ValueError("There are no mood records to analyze.")

    df = records[["date", "mood", "intensity"]].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["intensity"] = pd.to_numeric(
        df["intensity"], errors="coerce"
    )
    df["mood"] = df["mood"].astype("string").str.strip()

    df = df.dropna(subset=["date", "mood", "intensity"])
    df = df[df["mood"] != ""]

    if df.empty:
        raise ValueError("No valid mood records were found.")

    df["day"] = df["date"].dt.date

    mood_counts = Counter(df["mood"].tolist())
    most_common_mood, most_common_count = mood_counts.most_common(1)[0]

    daily_intensity = (
        df.groupby("day")["intensity"].mean().sort_index()
    )

    latest_day = pd.Timestamp(df["date"].max()).normalize()
    recent_start = latest_day - pd.Timedelta(days=6)
    previous_start = latest_day - pd.Timedelta(days=13)
    previous_end = latest_day - pd.Timedelta(days=7)

    recent = df[
        (df["date"] >= recent_start)
        & (df["date"] < latest_day + pd.Timedelta(days=1))
    ]
    previous = df[
        (df["date"] >= previous_start)
        & (df["date"] < previous_end + pd.Timedelta(days=1))
    ]

    recent_avg = (
        round(float(recent["intensity"].mean()), 2)
        if not recent.empty
        else None
    )
    previous_avg = (
        round(float(previous["intensity"].mean()), 2)
        if not previous.empty
        else None
    )

    change = None
    if recent_avg is not None and previous_avg is not None:
        change = round(recent_avg - previous_avg, 2)

    return {
        "total_checkins": len(df),
        "days_with_checkins": int(df["day"].nunique()),
        "date_range_start": str(df["date"].min().date()),
        "date_range_end": str(df["date"].max().date()),
        "average_intensity": round(float(df["intensity"].mean()), 2),
        "most_recorded_mood": str(most_common_mood),
        "most_recorded_mood_count": int(most_common_count),
        "mood_distribution": dict(mood_counts),
        "recent_7_day_checkins": len(recent),
        "recent_7_day_average_intensity": recent_avg,
        "previous_7_day_checkins": len(previous),
        "previous_7_day_average_intensity": previous_avg,
        "intensity_change": change,
        "daily_average_intensity": {
            str(day): round(float(value), 2)
            for day, value in daily_intensity.items()
        },
    }


def _create_fallback_insights(summary: dict) -> str:
    """Provide basic, data-grounded insights when the AI is unavailable."""

    lines = [
        "### Your mood reflection",
        (
            f"- You have recorded **{summary['total_checkins']} check-ins** "
            f"across **{summary['days_with_checkins']} days**."
        ),
        (
            f"- Your average recorded intensity is "
            f"**{summary['average_intensity']}/5**."
        ),
        (
            f"- Your most frequently recorded mood is "
            f"**{summary['most_recorded_mood']}** "
            f"({summary['most_recorded_mood_count']} check-ins)."
        ),
    ]

    change = summary["intensity_change"]

    if change is not None:
        if change < 0:
            interpretation = (
                "The average recorded intensity was lower in the recent "
                "seven-day period than in the previous seven days."
            )
        elif change > 0:
            interpretation = (
                "The average recorded intensity was higher in the recent "
                "seven-day period than in the previous seven days."
            )
        else:
            interpretation = (
                "The average recorded intensity was the same in both "
                "seven-day periods."
            )
        lines.append(f"- {interpretation}")
    else:
        lines.append(
            "- There are not enough records in both seven-day periods "
            "to compare them."
        )

    lines.extend(
        [
            "",
            "**A gentle next step:** Consider noting what was happening "
            "around a check-in and which everyday activities helped you "
            "feel supported.",
            "",
            "*These observations describe recorded check-ins only. "
            "They are not a diagnosis and do not explain why a mood occurred.*",
        ]
    )

    return "\n".join(lines)


def generate_mood_insights(records: pd.DataFrame) -> str:
    """Generate AI reflections using aggregate statistics, not journal notes."""

    summary = build_mood_summary(records)

    prompt = f"""
    You are MindTrack AI, a supportive wellness reflection assistant.

    Use only the following aggregated mood-tracking statistics:
    {summary}

    Write a concise, personalized reflection with these headings:
    1. What the records show
    2. Recent changes
    3. A gentle reflection question
    4. One small, optional wellbeing action

    Rules:
    - Describe patterns, not diagnoses.
    - Do not assume that higher or lower intensity is automatically good or bad.
    - Do not invent causes, events, emotions, or missing data.
    - If there are not enough check-ins to compare periods, say so.
    - Clearly distinguish recorded data from possibilities.
    - Use warm, non-judgmental language.
    - Do not claim to replace professional support.
    - Keep the response concise and practical.
    """

    try:
        response = generate_response(
            [{"role": "user", "content": prompt}]
        )

        if isinstance(response, str) and response.strip():
            return response.strip()

    except Exception as exc:
        # Keep technical details in the local terminal, not the UI.
        print(
            "MindTrack mood insights error: "
            f"{type(exc).__name__}: {exc}"
        )

    return _create_fallback_insights(summary)
