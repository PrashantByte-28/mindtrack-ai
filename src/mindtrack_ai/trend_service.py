"""Descriptive trend analysis for MindTrack AI mood records."""

import pandas as pd

WEEKDAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _empty_result() -> dict:
    """Return empty results when records are unavailable."""
    return {
        "daily_trend": pd.DataFrame(),
        "weekday_summary": pd.DataFrame(),
        "insights": [],
    }


def build_mood_trend_analysis(records: pd.DataFrame) -> dict:
    """Build rolling daily and weekday summaries from mood check-ins.

    Expected columns: date, mood, intensity.
    The input DataFrame is not modified.
    """
    required = {"date", "mood", "intensity"}

    if (
        records is None
        or records.empty
        or not required.issubset(records.columns)
    ):
        return _empty_result()

    df = records.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    ).dt.normalize()

    df["intensity"] = pd.to_numeric(
        df["intensity"],
        errors="coerce",
    )

    df["mood"] = df["mood"].astype("string").str.strip()

    df = df.dropna(
        subset=["date", "intensity", "mood"]
    )

    df = df[
        df["mood"].ne("")
        & df["intensity"].between(1, 5)
    ].copy()

    if df.empty:
        return _empty_result()

    df = df.sort_values("date")

    # Daily average intensity and number of check-ins.
    daily_trend = (
        df.groupby("date")
        .agg(
            average_intensity=("intensity", "mean"),
            check_ins=("intensity", "size"),
        )
        .sort_index()
        .asfreq("D")
    )

    # Missing dates have zero check-ins, but no fabricated intensity.
    daily_trend["check_ins"] = (
        daily_trend["check_ins"]
        .fillna(0)
        .astype(int)
    )

    daily_trend["rolling_7_day"] = (
        daily_trend["average_intensity"]
        .rolling(window=7, min_periods=1)
        .mean()
    )

    daily_trend = daily_trend.reset_index()

    # Check-in patterns by weekday.
    df["weekday"] = pd.Categorical(
        df["date"].dt.day_name(),
        categories=WEEKDAY_ORDER,
        ordered=True,
    )

    weekday_summary = (
        df.groupby("weekday", observed=False)
        .agg(
            check_ins=("intensity", "size"),
            average_intensity=("intensity", "mean"),
        )
        .reindex(WEEKDAY_ORDER)
        .dropna(subset=["average_intensity"])
        .reset_index()
    )

    weekday_summary["weekday"] = (
        weekday_summary["weekday"].astype(str)
    )

    # Generate descriptive trend reflections.
    insights = []

    recorded_days = sorted(
        df["date"].dropna().unique()
    )

    if len(recorded_days) >= 4:
        split_at = len(recorded_days) // 2

        earlier_days = recorded_days[:split_at]
        later_days = recorded_days[split_at:]

        earlier = df[df["date"].isin(earlier_days)]
        later = df[df["date"].isin(later_days)]

        earlier_mean = earlier["intensity"].mean()
        later_mean = later["intensity"].mean()

        difference = later_mean - earlier_mean

        if abs(difference) >= 0.3:
            direction = (
                "higher" if difference > 0 else "lower"
            )

            insights.append(
                f"Average recorded intensity was "
                f"{abs(difference):.2f} points {direction} "
                "in the later portion than in the earlier portion."
            )

        else:
            insights.append(
                "Average recorded intensity was relatively similar "
                "across the two portions of this period."
            )

        earlier_mood = earlier["mood"].mode()
        later_mood = later["mood"].mode()

        if not earlier_mood.empty and not later_mood.empty:
            if earlier_mood.iloc[0] == later_mood.iloc[0]:
                insights.append(
                    f"{earlier_mood.iloc[0]} was the most frequently "
                    "recorded mood in both portions of this period."
                )

            else:
                insights.append(
                    "The most frequently recorded mood changed "
                    f"from {earlier_mood.iloc[0]} earlier to "
                    f"{later_mood.iloc[0]} later."
                )

    else:
        insights.append(
            "Record check-ins on at least four different days to "
            "explore changes across the selected period."
        )

    if not weekday_summary.empty:
        busiest = weekday_summary.sort_values(
            ["check_ins", "weekday"],
            ascending=[False, True],
        ).iloc[0]

        insights.append(
            f"{busiest['weekday']} has the most check-ins in this "
            f"selection ({int(busiest['check_ins'])})."
        )

    insights.append(
        "These patterns describe recorded check-ins only. "
        "They cannot explain why a mood occurred or diagnose "
        "a mental health condition."
    )

    return {
        "daily_trend": daily_trend,
        "weekday_summary": weekday_summary,
        "insights": insights,
    }