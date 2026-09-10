"""
Database access layer for the Loan Portfolio Analytics dashboard.

Kept free of any Streamlit imports so it can be reused or tested
independently of the dashboard (scripts, notebooks, other apps, etc.).
"""

import os

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Default set of views the dashboard reads from.
DEFAULT_VIEWS = [
    "vw_monthly_issued_loans",
    "vw_agent_issued_most_loans",
    "vw_sales_loan_value_range",
    "vw_loans_by_team",
    "vw_repeat_clients",
    "vw_avg_time_to_second_loan",
    "vw_popular_loan_weekdays",
    "vw_popular_loan_types",
    "vw_applications_by_source",
    "vw_january_non_car_loans",
    "vw_avg_issuance_time_by_agent",
    "vw_avg_issuance_time_by_team",
    "vw_avg_time_first_change_to_issuance",
    "vw_daily_active_loans",
]


def get_db_engine() -> Engine:
    """Build a SQLAlchemy engine from environment variables (.env supported)."""
    load_dotenv(find_dotenv(), override=True)

    user = os.getenv("DB_USER", "appuser")
    password = os.getenv("PGPASSWORD")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "appdb")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


def fetch_views(engine: Engine = None, view_names=None, schema: str = None) -> dict:
    """Fetch one or more Postgres views into a dict of DataFrames.

    Args:
        engine: an existing SQLAlchemy engine. If None, one is created via
            get_db_engine() (and disposed of after use).
        view_names: list of view names to load. Defaults to DEFAULT_VIEWS.
        schema: schema the views live in. Defaults to the DB_SCHEMA env var,
            falling back to "Mogo".

    Returns:
        dict mapping view name -> DataFrame. Views that fail to load are
        skipped with a message printed to stdout (the caller decides how to
        surface that, e.g. st.warning in the dashboard).
    """
    if view_names is None:
        view_names = DEFAULT_VIEWS
    if schema is None:
        schema = os.getenv("DB_SCHEMA", "Mogo")

    owns_engine = engine is None
    if owns_engine:
        engine = get_db_engine()

    dfs = {}
    try:
        with engine.connect() as conn:
            for view in view_names:
                try:
                    dfs[view] = pd.read_sql(f'SELECT * FROM "{schema}".{view};', conn)
                    print(f"Loaded {view} ({len(dfs[view])} rows)")
                except Exception as e:
                    print(f"Could not load {view}: {e}")
    finally:
        if owns_engine:
            engine.dispose()

    return dfs
