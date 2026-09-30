"""Streamlit app for Chat with Your Data SQL."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.charts import build_chart
from src.config import SAMPLE_QUESTIONS
from src.database import AnalyticsDatabase
from src.insights import (
    recommendation_for_intent,
    summarize_generic,
    summarize_repeat_purchase,
    summarize_revenue_trend,
    summarize_top_customers,
    summarize_top_products,
)
from src.nl2sql import NL2SQLPlanner


st.set_page_config(page_title="Chat with Your Data SQL", layout="wide")


@st.cache_resource

def get_database() -> AnalyticsDatabase:
    db = AnalyticsDatabase()
    db.build()
    return db


@st.cache_resource

def get_planner() -> NL2SQLPlanner:
    return NL2SQLPlanner()


def render_insight(intent: str, df: pd.DataFrame) -> str:
    if intent == "revenue_trend":
        return summarize_revenue_trend(df)
    if intent == "top_products":
        return summarize_top_products(df)
    if intent == "top_customers":
        return summarize_top_customers(df)
    if intent == "repeat_purchase":
        return summarize_repeat_purchase(df)
    return summarize_generic(df)


@st.cache_data

def run_query(sql: str) -> pd.DataFrame:
    db = get_database()
    return db.query(sql)


def main() -> None:
    st.title("Chat with Your Data SQL")
    st.caption("Ask a business question, get SQL, a chart, and a plain-English recommendation.")

    db = get_database()
    planner = get_planner()

    with st.sidebar:
        st.header("Database")
        st.caption(f"Planner mode: {planner.mode.upper()}")
        st.write("Tables and views")
        st.write("\n".join(f"- {name}" for name in db.table_names()))
        st.markdown("---")
        st.subheader("Sample questions")
        for question in SAMPLE_QUESTIONS:
            if st.button(question, width='stretch'):
                st.session_state["question"] = question

    question = st.text_area(
        "Ask a question",
        value=st.session_state.get("question", "Show monthly revenue trend with moving average"),
        height=90,
        placeholder="Example: Which products generate the most revenue?",
    )

    if st.button("Run analysis", type="primary") or question:
        plan = planner.plan(question)
        result = run_query(plan.sql)

        c1, c2, c3 = st.columns(3)
        c1.metric("Rows returned", f"{len(result):,}")
        c2.metric("Intent", plan.intent.replace("_", " ").title())
        c3.metric("Suggested action", "Business recommendation generated")

        tab1, tab2, tab3 = st.tabs(["Answer", "SQL", "Data"])
        with tab1:
            st.subheader(plan.title)
            st.write(render_insight(plan.intent, result))
            st.info(recommendation_for_intent(plan.intent))
            chart = build_chart(result, plan.chart, plan.title)
            if chart is not None:
                st.plotly_chart(chart, width='stretch')
            st.dataframe(result, width='stretch')
        with tab2:
            st.code(plan.sql, language="sql")
        with tab3:
            st.dataframe(result, width='stretch')

    st.markdown("---")
    st.subheader("Why this project matters")
    st.write(
        "This app turns natural language into SQL against a real analytics database, then explains the result and shows a chart. "
        "It is designed for business users who need answers without writing SQL by hand."
    )


if __name__ == "__main__":
    main()
