# import libraries
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
import pandas as pd

# Load the engine
def get_db_engine():
    load_dotenv(find_dotenv(), override=True)

    user = os.getenv("DB_USER", "appuser")
    password = os.getenv("PGPASSWORD")
    host = os.getenv("DB_HOST", "127.0.0.1")
    dbname = os.getenv("DB_NAME", "appdb")

    url = f"postgresql+psycopy2://{user}:{password}@{host}:5432/{dbname}"
    return create_engine(url)

# fetch the views
def fetch_views(view_names=None):
    if view_names is None:
        view_names = [
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
            "vw_daily_active_loans"
        ]

        engine = get_db_engine()
        dfs = {}

        for view in view_names:
            dfs[view] = pd.read_sql(f'SELECT * FROM "Mogo".{view};', engine)
            print(f'Loaded {view} ({len(dfs[view])} rows)')
