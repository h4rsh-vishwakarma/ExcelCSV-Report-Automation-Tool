"""Auto-chart generation driven purely by detected column types — no hardcoded columns."""

import pandas as pd
import plotly.express as px

MAX_CATEGORIES = 15


def numeric_charts(df: pd.DataFrame, numeric_cols: list) -> list:
    charts = []
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        fig = px.histogram(df, x=col, title=f"Distribution of {col}", nbins=30)
        fig.update_layout(bargap=0.05)
        charts.append((f"dist_{col}", fig))
    return charts


def categorical_charts(df: pd.DataFrame, categorical_cols: list) -> list:
    charts = []
    for col in categorical_cols:
        n_unique = df[col].nunique(dropna=True)
        if n_unique == 0 or n_unique > MAX_CATEGORIES:
            continue
        counts = df[col].value_counts(dropna=True).reset_index()
        counts.columns = [col, "count"]
        if n_unique <= 6:
            fig = px.pie(counts, names=col, values="count", title=f"Share by {col}")
        else:
            fig = px.bar(counts, x=col, y="count", title=f"Count by {col}")
        charts.append((f"cat_{col}", fig))
    return charts


def date_trend_charts(df: pd.DataFrame, date_cols: list, numeric_cols: list) -> list:
    charts = []
    if not numeric_cols:
        return charts
    for date_col in date_cols:
        valid = df[[date_col] + numeric_cols].dropna(subset=[date_col])
        if valid.empty:
            continue
        for num_col in numeric_cols[:3]:  # cap to avoid an unbounded chart explosion
            trend = valid.groupby(pd.Grouper(key=date_col, freq="D"))[num_col].sum().reset_index()
            trend = trend[trend[num_col] != 0]
            if len(trend) < 2:
                continue
            fig = px.line(trend, x=date_col, y=num_col, title=f"{num_col} over time ({date_col})")
            charts.append((f"trend_{date_col}_{num_col}", fig))
    return charts


def auto_generate_charts(df: pd.DataFrame, column_types: dict) -> list:
    """Returns list of (key, plotly Figure) tuples."""
    charts = []
    charts += date_trend_charts(df, column_types["date"], column_types["numeric"])
    charts += numeric_charts(df, column_types["numeric"])
    charts += categorical_charts(df, column_types["categorical"])
    return charts
