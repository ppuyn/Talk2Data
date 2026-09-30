"""Chart builders for SQL query results."""

from __future__ import annotations

import pandas as pd
import plotly.express as px


def build_chart(df: pd.DataFrame, chart_type: str, title: str):
    if df.empty:
        return None
    if chart_type == "line":
        x = df.columns[0]
        y = next((c for c in df.columns if c in {"revenue", "repeat_rate", "moving_avg_3m", "rolling_3m_repeat_rate"}), df.columns[1])
        fig = px.line(df, x=x, y=y, markers=True, title=title)
        if "moving_avg_3m" in df.columns and y != "moving_avg_3m":
            fig.add_scatter(x=df[x], y=df["moving_avg_3m"], mode="lines", name="3M Moving Avg")
        return fig
    if chart_type == "bar":
        x = df.columns[0]
        y = next((c for c in df.columns if c not in {x} and pd.api.types.is_numeric_dtype(df[c])), df.columns[1])
        color = x if x in df.columns else None
        return px.bar(df, x=x, y=y, color=color, title=title)
    if chart_type == "scatter":
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric_cols) < 2:
            return None
        return px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], color=df.columns[0], title=title)
    return None
