"""SQLite database creation and querying."""

from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd

try:  # pragma: no cover
    from .config import DB_PATH
    from .data import SyntheticDataGenerator
except ImportError:  # pragma: no cover
    from config import DB_PATH
    from data import SyntheticDataGenerator


class AnalyticsDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)

    def build(self, overwrite: bool = False) -> Path:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if overwrite and self.db_path.exists():
            self.db_path.unlink()
        if self.db_path.exists():
            return self.db_path

        generator = SyntheticDataGenerator()
        frames = generator.build_frames()
        with sqlite3.connect(self.db_path) as conn:
            for name, frame in frames.items():
                frame.to_sql(name, conn, index=False, if_exists="replace")
            self._create_order_metrics(conn)
            self._create_catalog_view(conn)
        return self.db_path

    def _create_order_metrics(self, conn: sqlite3.Connection) -> None:
        conn.execute("DROP VIEW IF EXISTS order_metrics")
        conn.execute(
            """
            CREATE VIEW order_metrics AS
            SELECT
                o.order_id,
                o.customer_id,
                o.order_date,
                o.channel,
                o.status,
                o.shipping_type,
                o.discount_rate,
                COUNT(oi.line_no) AS item_count,
                SUM(oi.quantity) AS units,
                ROUND(SUM(oi.line_revenue), 2) AS gross_revenue,
                ROUND(SUM(oi.line_revenue) * (1 - o.discount_rate), 2) AS net_revenue
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            GROUP BY 1,2,3,4,5,6,7
            """
        )

    def _create_catalog_view(self, conn: sqlite3.Connection) -> None:
        conn.execute("DROP VIEW IF EXISTS product_catalog")
        conn.execute(
            """
            CREATE VIEW product_catalog AS
            SELECT
                p.product_id,
                p.product_name,
                p.category,
                p.subcategory,
                p.base_price,
                p.cost,
                p.launch_date,
                COALESCE(om.order_count, 0) AS order_count,
                COALESCE(om.category_revenue, 0) AS category_revenue
            FROM products p
            LEFT JOIN (
                SELECT
                    oi.product_id,
                    COUNT(DISTINCT oi.order_id) AS order_count,
                    SUM(oi.line_revenue) AS category_revenue
                FROM order_items oi
                GROUP BY 1
            ) om ON p.product_id = om.product_id
            """
        )

    def query(self, sql: str) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(sql, conn)

    def table_names(self) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        return [row[0] for row in rows]
