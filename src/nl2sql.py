"""Natural-language to SQL planner with an LLM-backed option.

The planner uses OpenAI when an API key is available and falls back to a
transparent rule-based template planner when the model is unavailable or
returns invalid output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import json
import os
import re

try:  # pragma: no cover
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


SUPPORTED_INTENTS = {
    "revenue_trend": {
        "title": "Monthly revenue trend",
        "chart": "line",
        "hint": "Use this to monitor growth, seasonality, and moving averages.",
    },
    "top_products": {
        "title": "Top products by net revenue",
        "chart": "bar",
        "hint": "Identify the products and categories driving the most revenue.",
    },
    "top_customers": {
        "title": "Top customers by lifetime value",
        "chart": "bar",
        "hint": "Prioritize retention for the highest-value accounts.",
    },
    "repeat_purchase": {
        "title": "Monthly repeat purchase rate",
        "chart": "line",
        "hint": "Track retention and identify months where repeat buying improves or declines.",
    },
    "aov_by_channel": {
        "title": "Average order value by acquisition channel",
        "chart": "bar",
        "hint": "Highlight which channels attract higher-spending customers.",
    },
    "basket_mix": {
        "title": "Product bundle opportunity",
        "chart": "bar",
        "hint": "Spot common product combinations for bundling and cross-sell.",
    },
    "category_momentum": {
        "title": "Category momentum and revenue mix",
        "chart": "bar",
        "hint": "See which categories are gaining share and which need attention.",
    },
}

QUESTION_PATTERNS = [
    ("top_products", ["top product", "best product", "which products", "product generate the most revenue", "products generate the most revenue"]),
    ("top_customers", ["top customer", "lifetime value", "best customers", "customer value"]),
    ("repeat_purchase", ["repeat purchase", "retention", "repeat rate"]),
    ("aov_by_channel", ["average order value", "aov", "channel"]),
    ("basket_mix", ["basket", "cross sell", "bundle", "frequently bought together"]),
    ("category_momentum", ["category", "margin", "category momentum"]),
    ("revenue_trend", ["revenue trend", "monthly revenue", "moving average", "revenue"]),
]

ALLOWED_TABLES = {
    "customers",
    "products",
    "orders",
    "order_items",
    "order_metrics",
    "product_catalog",
}

SQL_BLOCKLIST = re.compile(r"\b(insert|update|delete|drop|alter|truncate|attach|detach|replace|pragma|vacuum|create\s+table)\b", re.IGNORECASE)
SQL_START = re.compile(r"^\s*(with|select)\b", re.IGNORECASE | re.DOTALL)


@dataclass
class QueryPlan:
    intent: str
    sql: str
    chart: str
    title: str
    insight_hint: str


class NL2SQLPlanner:
    """LLM-backed SQL planner with deterministic fallback templates."""

    def __init__(self, model: Optional[str] = None, prefer_llm: bool = True):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.prefer_llm = prefer_llm
        self.mode = "fallback"
        self._client = None
        if prefer_llm and OpenAI is not None and os.getenv("OPENAI_API_KEY"):
            try:
                self._client = OpenAI()
                self.mode = "llm"
            except Exception:
                self._client = None
                self.mode = "fallback"

    def detect_intent(self, question: str) -> str:
        q = question.lower()
        for intent, phrases in QUESTION_PATTERNS:
            for phrase in phrases:
                if phrase in q:
                    return intent
        return "revenue_trend"

    def plan(self, question: str) -> QueryPlan:
        if self._client is not None:
            llm_plan = self._plan_with_llm(question)
            if llm_plan is not None:
                self.mode = "llm"
                return llm_plan

        self.mode = "fallback"
        return self._plan_with_templates(question)

    def _plan_with_llm(self, question: str) -> Optional[QueryPlan]:
        prompt = self._system_prompt(question)
        try:
            response = self._client.chat.completions.create(  # type: ignore[union-attr]
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": question},
                ],
            )
            content = response.choices[0].message.content or "{}"
            payload = json.loads(content)
            return self._validate_llm_payload(payload, question)
        except Exception:
            return None

    def _validate_llm_payload(self, payload: dict[str, Any], question: str) -> Optional[QueryPlan]:
        intent = str(payload.get("intent", self.detect_intent(question))).strip()
        sql = str(payload.get("sql", "")).strip()
        title = str(payload.get("title", SUPPORTED_INTENTS.get(intent, SUPPORTED_INTENTS["revenue_trend"])["title"]))
        chart = str(payload.get("chart", SUPPORTED_INTENTS.get(intent, SUPPORTED_INTENTS["revenue_trend"])["chart"]))
        insight_hint = str(payload.get("insight_hint", SUPPORTED_INTENTS.get(intent, SUPPORTED_INTENTS["revenue_trend"])["hint"]))

        if intent not in SUPPORTED_INTENTS:
            intent = self.detect_intent(question)
        if chart not in {"line", "bar", "scatter"}:
            chart = SUPPORTED_INTENTS[intent]["chart"]
        if not self._is_safe_sql(sql):
            return None
        return QueryPlan(intent=intent, sql=sql, chart=chart, title=title, insight_hint=insight_hint)

    def _is_safe_sql(self, sql: str) -> bool:
        if not sql or not SQL_START.search(sql):
            return False
        if SQL_BLOCKLIST.search(sql):
            return False
        lowered = sql.lower()
        if "--" in sql or "/*" in sql:
            return False
        if ";" in sql.strip().rstrip(";"):
            return False
        if not any(table in lowered for table in ALLOWED_TABLES):
            return False
        return True

    def _system_prompt(self, question: str) -> str:
        schema = """
You are a senior analytics engineer. Convert the user's business question into a single safe SQLite query.

Available tables and views:
- customers(customer_id, customer_name, segment, city, region, signup_date, acquisition_channel)
- products(product_id, product_name, category, subcategory, base_price, cost, launch_date)
- orders(order_id, customer_id, order_date, channel, status, shipping_type, discount_rate)
- order_items(order_id, line_no, product_id, quantity, unit_price, line_revenue)
- order_metrics(order_id, customer_id, order_date, channel, status, shipping_type, discount_rate, item_count, units, gross_revenue, net_revenue)
- product_catalog(product_id, product_name, category, subcategory, base_price, cost, launch_date, order_count, category_revenue)

Rules:
- Return JSON only with keys: intent, title, chart, sql, insight_hint.
- Only use SELECT or WITH queries.
- Prefer CTEs and window functions when useful.
- Use only the tables and views listed above.
- Do not invent columns.
- Keep the SQL readable.
- Chart must be one of: line, bar, scatter.
- Choose intent from: revenue_trend, top_products, top_customers, repeat_purchase, aov_by_channel, basket_mix, category_momentum.
- If the question is ambiguous, choose the best fit and explain in insight_hint.

Examples:
- 'Which products generate the most revenue?' -> top_products
- 'Who are the top customers by lifetime value?' -> top_customers
- 'What is the repeat purchase rate by month?' -> repeat_purchase
- 'Which channels produce the highest average order value?' -> aov_by_channel
- 'Show monthly revenue trend with moving average' -> revenue_trend

Question: {question}
""".strip()
        return schema.format(question=question)

    def _plan_with_templates(self, question: str) -> QueryPlan:
        intent = self.detect_intent(question)
        if intent == "top_products":
            return QueryPlan(intent=intent, sql=self._sql_top_products(), chart="bar", title=SUPPORTED_INTENTS[intent]["title"], insight_hint=SUPPORTED_INTENTS[intent]["hint"])
        if intent == "top_customers":
            return QueryPlan(intent=intent, sql=self._sql_top_customers(), chart="bar", title=SUPPORTED_INTENTS[intent]["title"], insight_hint=SUPPORTED_INTENTS[intent]["hint"])
        if intent == "repeat_purchase":
            return QueryPlan(intent=intent, sql=self._sql_repeat_purchase(), chart="line", title=SUPPORTED_INTENTS[intent]["title"], insight_hint=SUPPORTED_INTENTS[intent]["hint"])
        if intent == "aov_by_channel":
            return QueryPlan(intent=intent, sql=self._sql_aov_by_channel(), chart="bar", title=SUPPORTED_INTENTS[intent]["title"], insight_hint=SUPPORTED_INTENTS[intent]["hint"])
        if intent == "basket_mix":
            return QueryPlan(intent=intent, sql=self._sql_basket_mix(), chart="bar", title=SUPPORTED_INTENTS[intent]["title"], insight_hint=SUPPORTED_INTENTS[intent]["hint"])
        if intent == "category_momentum":
            return QueryPlan(intent=intent, sql=self._sql_category_momentum(), chart="bar", title=SUPPORTED_INTENTS[intent]["title"], insight_hint=SUPPORTED_INTENTS[intent]["hint"])
        return QueryPlan(intent="revenue_trend", sql=self._sql_revenue_trend(), chart="line", title=SUPPORTED_INTENTS["revenue_trend"]["title"], insight_hint=SUPPORTED_INTENTS["revenue_trend"]["hint"])

    def _sql_revenue_trend(self) -> str:
        return """
        WITH monthly AS (
            SELECT
                strftime('%Y-%m', order_date) AS month,
                SUM(net_revenue) AS revenue,
                COUNT(DISTINCT order_id) AS orders
            FROM order_metrics
            GROUP BY 1
        ),
        trend AS (
            SELECT
                month,
                revenue,
                orders,
                AVG(revenue) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving_avg_3m,
                LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue
            FROM monthly
        )
        SELECT
            month,
            revenue,
            orders,
            moving_avg_3m,
            ROUND((revenue - prev_month_revenue) / NULLIF(prev_month_revenue, 0), 4) AS mom_growth
        FROM trend
        ORDER BY month;
        """

    def _sql_top_products(self) -> str:
        return """
        WITH product_sales AS (
            SELECT
                oi.product_id,
                p.product_name,
                p.category,
                SUM(oi.line_revenue) AS revenue,
                SUM(oi.quantity) AS units,
                COUNT(DISTINCT oi.order_id) AS orders
            FROM order_items oi
            JOIN products p ON p.product_id = oi.product_id
            GROUP BY 1,2,3
        ),
        ranked AS (
            SELECT
                *,
                DENSE_RANK() OVER (ORDER BY revenue DESC) AS revenue_rank,
                SUM(revenue) OVER () AS total_revenue
            FROM product_sales
        )
        SELECT
            product_name,
            category,
            revenue,
            units,
            orders,
            revenue_rank,
            ROUND(revenue / NULLIF(total_revenue, 0), 4) AS revenue_share
        FROM ranked
        WHERE revenue_rank <= 15
        ORDER BY revenue DESC;
        """

    def _sql_top_customers(self) -> str:
        return """
        WITH customer_value AS (
            SELECT
                o.customer_id,
                c.customer_name,
                c.segment,
                c.region,
                COUNT(DISTINCT o.order_id) AS orders,
                SUM(o.net_revenue) AS lifetime_value,
                AVG(o.net_revenue) AS avg_order_value,
                MAX(date(o.order_date)) AS last_order_date
            FROM order_metrics o
            JOIN customers c ON c.customer_id = o.customer_id
            GROUP BY 1,2,3,4
        ),
        scored AS (
            SELECT
                *,
                NTILE(5) OVER (ORDER BY lifetime_value DESC) AS value_quintile,
                ROW_NUMBER() OVER (ORDER BY lifetime_value DESC) AS customer_rank
            FROM customer_value
        )
        SELECT
            customer_id,
            customer_name,
            segment,
            region,
            orders,
            lifetime_value,
            avg_order_value,
            value_quintile,
            customer_rank,
            last_order_date
        FROM scored
        WHERE customer_rank <= 20
        ORDER BY lifetime_value DESC;
        """

    def _sql_repeat_purchase(self) -> str:
        return """
        WITH customer_orders AS (
            SELECT
                customer_id,
                DATE(order_date) AS order_day,
                strftime('%Y-%m', order_date) AS month,
                ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS order_seq,
                LAG(DATE(order_date)) OVER (PARTITION BY customer_id ORDER BY order_date) AS prev_order_day
            FROM order_metrics
        ),
        repeat_flags AS (
            SELECT
                month,
                customer_id,
                CASE
                    WHEN prev_order_day IS NOT NULL THEN 1 ELSE 0
                END AS is_repeat
            FROM customer_orders
        ),
        monthly AS (
            SELECT
                month,
                COUNT(DISTINCT customer_id) AS active_customers,
                SUM(is_repeat) AS repeat_customer_events,
                SUM(is_repeat) * 1.0 / COUNT(DISTINCT customer_id) AS repeat_rate
            FROM repeat_flags
            GROUP BY 1
        )
        SELECT
            month,
            active_customers,
            repeat_customer_events,
            ROUND(repeat_rate, 4) AS repeat_rate,
            AVG(repeat_rate) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS rolling_3m_repeat_rate
        FROM monthly
        ORDER BY month;
        """

    def _sql_aov_by_channel(self) -> str:
        return """
        WITH channel_stats AS (
            SELECT
                channel,
                COUNT(DISTINCT order_id) AS orders,
                AVG(net_revenue) AS avg_order_value,
                SUM(net_revenue) AS revenue,
                AVG(discount_rate) AS avg_discount
            FROM order_metrics
            GROUP BY 1
        )
        SELECT
            channel,
            orders,
            ROUND(avg_order_value, 2) AS avg_order_value,
            ROUND(revenue, 2) AS revenue,
            ROUND(avg_discount, 4) AS avg_discount
        FROM channel_stats
        ORDER BY avg_order_value DESC;
        """

    def _sql_basket_mix(self) -> str:
        return """
        WITH pair_orders AS (
            SELECT
                a.product_id AS product_a,
                b.product_id AS product_b,
                COUNT(*) AS co_orders
            FROM order_items a
            JOIN order_items b ON a.order_id = b.order_id AND a.product_id < b.product_id
            GROUP BY 1,2
        ),
        enriched AS (
            SELECT
                po.product_a,
                pa.product_name AS product_a_name,
                pa.category AS category_a,
                po.product_b,
                pb.product_name AS product_b_name,
                pb.category AS category_b,
                po.co_orders,
                DENSE_RANK() OVER (ORDER BY po.co_orders DESC) AS pair_rank
            FROM pair_orders po
            JOIN products pa ON pa.product_id = po.product_a
            JOIN products pb ON pb.product_id = po.product_b
        )
        SELECT
            product_a_name,
            category_a,
            product_b_name,
            category_b,
            co_orders,
            pair_rank
        FROM enriched
        WHERE pair_rank <= 15
        ORDER BY co_orders DESC;
        """

    def _sql_category_momentum(self) -> str:
        return """
        WITH monthly_category AS (
            SELECT
                strftime('%Y-%m', o.order_date) AS month,
                p.category,
                SUM(oi.line_revenue) AS revenue
            FROM order_metrics o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON p.product_id = oi.product_id
            GROUP BY 1,2
        ),
        category_share AS (
            SELECT
                month,
                category,
                revenue,
                SUM(revenue) OVER (PARTITION BY month) AS month_total,
                LAG(revenue) OVER (PARTITION BY category ORDER BY month) AS prev_revenue
            FROM monthly_category
        )
        SELECT
            month,
            category,
            revenue,
            ROUND(revenue / NULLIF(month_total, 0), 4) AS revenue_share,
            ROUND((revenue - prev_revenue) / NULLIF(prev_revenue, 0), 4) AS mom_growth
        FROM category_share
        ORDER BY month, revenue DESC;
        """
