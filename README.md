# Talk2Data

Ask a natural-language business question, get back the SQL, and see a charted answer from a real SQLite analytics database.

[![Open in Streamlit]([https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://gdp-dashboard-template.streamlit.app/](https://talk2data-7gcvjj7c7vkxmsg4rqbotz.streamlit.app/))

## Problem

Business users often know the question they want answered, but not SQL. This project bridges that gap:

- natural-language question in
- SQL generated from the question
- chart and table returned
- plain-English insight and business recommendation
* The schema is designed to support real analytics questions like revenue trends, customer lifetime value, repeat purchase rate, and product bundle opportunities.

## How to run

```bash
cd chat-with-your-data-sql
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```
---
## Data

This project ships with a synthetic retail analytics database built from four tables:

- `customers`
- `products`
- `orders`
- `order_items`

The app also creates derived views such as:

- `order_metrics`
- `product_catalog`
  
## Method

The app uses an LLM-backed natural-language-to-SQL planner when an OpenAI API key is available. If the API key is missing, it falls back to deterministic intent templates so the project still runs locally.

Supported SQL patterns include:

- CTEs
- window functions such as `LAG`, `AVG() OVER`, `NTILE`, `ROW_NUMBER`, `DENSE_RANK`
- grouped aggregations
- ranked leaderboards
- bundle / co-purchase analysis

### LLM-backed planning

- Set `OPENAI_API_KEY` in your environment or `.env`
- Optional model override: `OPENAI_MODEL=gpt-4o-mini`
- The app returns JSON with the chosen intent, SQL, chart type, title, and insight hint
- If the model response is invalid, the app safely falls back to the template planner

## Results from the demo database

Example outputs from the generated SQLite dataset:

- Monthly revenue started at about **244K** in the first month and grew steadily over the next months.
- The top products by revenue included **Product 54**, **Product 76**, and **Product 27**.
- The top customer by lifetime value reached about **10.0K** in spend across **11** orders.
- Repeat purchase rate increased from about **12.2%** in January to **57.3%** by March in the demo run.
- Among channels, **Marketplace** produced the highest average order value at about **677.66**, while **Web** contributed the highest total revenue.

## Business recommendation

Use the app to identify where to focus growth and retention actions:

- prioritize retention for top-value customers
- bundle products that frequently co-occur
- invest in channels with stronger order value
- watch the 3-month moving average for revenue dips
- run lifecycle campaigns when repeat purchase rate drops

## How it works

1. A SQLite database is generated automatically on first run.
2. The planner maps your question to a SQL template.
3. The query is executed against the database.
4. A chart and insight are rendered in Streamlit.

## Sample questions

- Show monthly revenue trend with moving average
- Which products generate the most revenue?
- Who are the top customers by lifetime value?
- What is the repeat purchase rate by month?
- Which channels produce the highest average order value?


## Repository structure

```text
chat-with-your-data-sql/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── data/
├── artifacts/
└── src/
    ├── __init__.py
    ├── config.py
    ├── data.py
    ├── database.py
    ├── nl2sql.py
    ├── insights.py
    └── charts.py
```

## Notes

- The app is intentionally clean and notebook-free.
- SQL is visible in the UI so reviewers can verify the logic.
- The database and business logic are separated into small, readable modules.
- The planner is LLM-backed but has a deterministic fallback for reliability.
