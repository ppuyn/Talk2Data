"""Synthetic analytics database generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:  # pragma: no cover
    from .config import DATA_DIR, DB_PATH, SEED
except ImportError:  # pragma: no cover
    from config import DATA_DIR, DB_PATH, SEED


@dataclass
class SyntheticDataGenerator:
    n_customers: int = 1500
    n_products: int = 120
    n_orders: int = 7000
    seed: int = SEED

    def customers(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        cities = ["Austin", "Seattle", "Chicago", "New York", "Miami", "Denver", "Boston", "San Francisco"]
        regions = ["South", "West", "Midwest", "Northeast", "South", "West", "Northeast", "West"]
        segments = ["Consumer", "Corporate", "Home Office", "Enterprise"]
        channels = ["Organic", "Paid Search", "Email", "Direct", "Social"]

        ids = [f"C{idx:05d}" for idx in range(1, self.n_customers + 1)]
        chosen_cities = rng.choice(cities, size=self.n_customers)
        return pd.DataFrame(
            {
                "customer_id": ids,
                "customer_name": [f"Customer {idx}" for idx in range(1, self.n_customers + 1)],
                "segment": rng.choice(segments, size=self.n_customers, p=[0.46, 0.22, 0.18, 0.14]),
                "city": chosen_cities,
                "region": [regions[cities.index(city)] for city in chosen_cities],
                "signup_date": pd.to_datetime("2023-01-01") + pd.to_timedelta(rng.integers(0, 730, size=self.n_customers), unit="D"),
                "acquisition_channel": rng.choice(channels, size=self.n_customers, p=[0.28, 0.22, 0.18, 0.2, 0.12]),
            }
        )

    def products(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + 1)
        categories = ["Electronics", "Home", "Office", "Beauty", "Sports", "Kitchen"]
        subcats = {
            "Electronics": ["Audio", "Wearables", "Accessories"],
            "Home": ["Decor", "Cleaning", "Furniture"],
            "Office": ["Supplies", "Furniture", "Tech"],
            "Beauty": ["Skincare", "Haircare", "Tools"],
            "Sports": ["Fitness", "Outdoor", "Equipment"],
            "Kitchen": ["Cookware", "Appliances", "Storage"],
        }
        ids = [f"P{idx:05d}" for idx in range(1, self.n_products + 1)]
        category = rng.choice(categories, size=self.n_products)
        return pd.DataFrame(
            {
                "product_id": ids,
                "product_name": [f"Product {idx}" for idx in range(1, self.n_products + 1)],
                "category": category,
                "subcategory": [rng.choice(subcats[c]) for c in category],
                "base_price": np.round(rng.uniform(8, 250, size=self.n_products), 2),
                "cost": np.round(rng.uniform(3, 120, size=self.n_products), 2),
                "launch_date": pd.to_datetime("2023-01-01") + pd.to_timedelta(rng.integers(0, 365, size=self.n_products), unit="D"),
            }
        )

    def orders(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + 2)
        order_ids = [f"O{idx:06d}" for idx in range(1, self.n_orders + 1)]
        customer_ids = [f"C{idx:05d}" for idx in rng.integers(1, self.n_customers + 1, size=self.n_orders)]
        order_dates = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 540, size=self.n_orders), unit="D")
        order_dates = order_dates + pd.to_timedelta(rng.integers(8, 20, size=self.n_orders), unit="h")
        channels = rng.choice(["Web", "Mobile", "Marketplace"], size=self.n_orders, p=[0.46, 0.34, 0.20])
        statuses = rng.choice(["Completed", "Completed", "Completed", "Returned", "Cancelled"], size=self.n_orders, p=[0.73, 0.05, 0.02, 0.13, 0.07])
        shipping = rng.choice(["Standard", "Express"], size=self.n_orders, p=[0.76, 0.24])
        discount = np.round(np.clip(rng.normal(loc=0.08, scale=0.06, size=self.n_orders), 0, 0.35), 2)

        return pd.DataFrame(
            {
                "order_id": order_ids,
                "customer_id": customer_ids,
                "order_date": order_dates,
                "channel": channels,
                "status": statuses,
                "shipping_type": shipping,
                "discount_rate": discount,
            }
        )

    def order_items(self, orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + 3)
        records = []
        product_ids = products["product_id"].tolist()
        for order_id in orders["order_id"]:
            item_count = int(np.clip(rng.poisson(1.7) + 1, 1, 6))
            chosen = rng.choice(product_ids, size=item_count, replace=False)
            for line_no, product_id in enumerate(chosen, start=1):
                product = products.loc[products["product_id"] == product_id].iloc[0]
                qty = int(np.clip(rng.poisson(1.2) + 1, 1, 4))
                unit_price = float(product["base_price"])
                records.append(
                    {
                        "order_id": order_id,
                        "line_no": line_no,
                        "product_id": product_id,
                        "quantity": qty,
                        "unit_price": unit_price,
                        "line_revenue": round(qty * unit_price, 2),
                    }
                )
        return pd.DataFrame(records)

    def build_frames(self) -> dict[str, pd.DataFrame]:
        customers = self.customers()
        products = self.products()
        orders = self.orders()
        order_items = self.order_items(orders, products)
        return {"customers": customers, "products": products, "orders": orders, "order_items": order_items}

    def ensure_data_dir(self) -> Path:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR
