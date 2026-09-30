"""Insight generation for query results."""

from __future__ import annotations

import pandas as pd


def summarize_revenue_trend(df: pd.DataFrame) -> str:
    if df.empty:
        return "No rows returned."
    first = df.iloc[0]
    last = df.iloc[-1]
    growth = last.get("mom_growth")
    growth_text = f", with {growth:.1%} month-over-month growth in the latest period" if pd.notna(growth) else ""
    return (
        f"Revenue moved from {first['revenue']:,.0f} to {last['revenue']:,.0f} across the selected window{growth_text}."
    )


def summarize_top_products(df: pd.DataFrame) -> str:
    if df.empty:
        return "No product data returned."
    top = df.iloc[0]
    return f"{top['product_name']} leads revenue with {top['revenue']:,.0f} in sales and a {top['revenue_share']:.1%} share of the result set."


def summarize_top_customers(df: pd.DataFrame) -> str:
    if df.empty:
        return "No customer data returned."
    top = df.iloc[0]
    return f"{top['customer_name']} is the top customer with lifetime value of {top['lifetime_value']:,.0f} across {int(top['orders'])} orders."


def summarize_repeat_purchase(df: pd.DataFrame) -> str:
    if df.empty:
        return "No repeat purchase data returned."
    first = df.iloc[0]
    last = df.iloc[-1]
    return f"Repeat purchase rate changed from {first['repeat_rate']:.1%} to {last['repeat_rate']:.1%} over the period."


def summarize_generic(df: pd.DataFrame) -> str:
    return f"The query returned {len(df):,} rows."


def recommendation_for_intent(intent: str) -> str:
    mapping = {
        "revenue_trend": "Use the moving average to detect seasonality early and plan campaigns around weak months.",
        "top_products": "Protect your best sellers with inventory planning and bundle them into upsell offers.",
        "top_customers": "Treat top customers as a retention priority with loyalty perks and proactive outreach.",
        "repeat_purchase": "Run lifecycle campaigns when repeat rates dip and reinforce post-purchase reminders.",
        "aov_by_channel": "Put more budget into the channel with the highest average order value.",
        "basket_mix": "Create bundles for frequently co-purchased products to increase cart size.",
        "category_momentum": "Invest in categories with growing share and review pricing on declining categories.",
    }
    return mapping.get(intent, "Use the output to target the most valuable customers and product combinations.")
