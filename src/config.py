"""Project configuration."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DB_PATH = DATA_DIR / "analytics.db"
SEED = 42

SAMPLE_QUESTIONS = [
    "Show monthly revenue trend with moving average",
    "Which products generate the most revenue?",
    "Who are the top customers by lifetime value?",
    "What is the repeat purchase rate by month?",
    "Which channels produce the highest average order value?",
]
