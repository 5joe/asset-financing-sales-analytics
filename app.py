import streamlit as st
import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title = "Mogo Analytics!!", page_icon = ":bar_chart:", layout = "wide")

st.title("Mogo MotorCycle and Vehicle loan Analytics")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>',unsafe_allow_html=True)
# -- Load the db --
load_dotenv(find_dotenv(), override = True)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASSWORD = os.getenv("PGPASSWORD")

@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
    )

VIEWS = [
    "vw_agent_issued_most_loans",
        "vw_sales_loan_value_range",
        "vw_monthly_issued_loans",
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

@st.cache_data(ttl=3600)
def load_data():
    engine = get_engine()
    dfs = {}
    with engine.connect() as conn:
        for view in VIEWS:
            try:
                dfs[view] = pd.read_sql(f'SELECT * FROM "Mogo".{view};', conn)
            except Exception as e:
                st.warning(f"Could not load {view}: {e}")
    return dfs

dfs = load_data()

# -- Spinner for data loading --
with st.spinner("Loading loan data..."):
    dfs = load_data()

with st.sidebar:
    st.header("Controls")
    if st.button("🔄 Refresh data"):
        load_data.clear()
        st.rerun()

loans_by_month = dfs["vw_monthly_issued_loans"]

col1, col2 = st.columns(2)
with col1:
    st.subheader("Month Loan Issuance Trajectory")
    fig = px.bar(loans_by_month,
                 x = "month_name",
                 y = "loans_issued",
                 template = "seaborn")
    fig.update_layout(
        xaxis=dict(title = "Month", showgrid = True),
        yaxis=dict(title = "Loans Issued", showgrid = True)
    )
    st.plotly_chart(fig, use_container_width=True)


loans_by_team = dfs["vw_loans_by_team"]
with col2:
    st.subheader("Total Loan Issuance Breakdown by Team")
    fig = px.pie(
        loans_by_team,
        values = "loans_issued",
        names = "final_team",
        hole = 0.7
                 )
    fig.update_traces(text = loans_by_team["final_team"],
                      textposition = "inside")
    fig.update_layout(showlegend = False)
    st.plotly_chart(fig, use_container_width=True)

dwn1, dwn2 = st.columns(2)
with dwn1:
    with st.expander("Monthly Loan Issuance"):
        st.write(loans_by_month.style.background_gradient(cmap = "Blues"))
        csv = loans_by_month.to_csv(index = False).encode("utf-8")
        st.download_button("Download Data", data = csv, file_name = "Loans_by_Month.csv", mime = "text/csv",
                           help = "Click here to download the data as a CSV file")

with dwn2:
    with st.expander("Loan Issuance by Team"):
        st.write(loans_by_team.style.background_gradient(cmap = "Oranges"))
        csv = loans_by_team.to_csv(index = False).encode("utf-8")
        st.download_button("Download Data", data = csv, file_name = "Loans_by_Team.csv", mime ="text/csv",
                           help = "Click here to download the data as a CSV file")

st.divider()

col3, col4 = st.columns(2)

# -- Agent Performances --
loans_by_agent = dfs["vw_agent_issued_most_loans"]
with col3:
    st.subheader("Agent Performances in terms of loans issued")
    fig =px.bar(loans_by_agent,
                x = "loan_agent_name",
                y = "loans_issued_by_agent",
                template = "seaborn")
    fig.update_traces(text = loans_by_agent["loans_issued_by_agent"],
                      textposition = "inside"
                      )
    fig.update_layout(
        xaxis=dict(title = "Loan Agents", showgrid = True),
        yaxis=dict(title = "Loans Issued", showgrid = True)
        )
    st.plotly_chart(fig, use_container_width=True)

# -- Applications by Acquisition Channel Source --
applications_by_source = dfs["vw_applications_by_source"]

with col4:
    st.subheader("Applications by Acquisition Channel Source")
    
    # Create figure with a secondary Y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add Total Applications (Left Y-Axis)
    fig.add_trace(
        go.Bar(
            name="Total Applications",
            x=applications_by_source["source"],
            y=applications_by_source["total_applications"],
            offsetgroup=1,
        ),
        secondary_y=False,
    )

    # Add Total Issued Value (Right Y-Axis)
    fig.add_trace(
        go.Bar(
            name="Total Issued Value",
            x=applications_by_source["source"],
            y=applications_by_source["total_issued_value"],
            offsetgroup=2,
        ),
        secondary_y=True,
    )

    # Configure layout, axis titles, and grouping
    fig.update_layout(
        barmode="group",
        template="seaborn",
        showlegend=False
    )
    fig.update_yaxes(title_text="Total Applications", secondary_y=False)
    fig.update_yaxes(title_text="Total Issued Value", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

# -- download the data --
dwn3, dwn4 = st.columns(2)

with dwn3:
    with st.expander("Loans issued by Agents"):
        st.write(loans_by_agent.style.background_gradient(cmap = "Blues"))
        csv = loans_by_agent.to_csv(index = False).encode("utf-8")
        st.download_button("Download Data", data = csv, file_name="loans_by_agent.csv", mime = "text/csv",
                           help = "Click here to download the data as CSV file")

with dwn4:
    with st.expander("Applications by Acquisition Channel Source"):
        st.write(applications_by_source.style.background_gradient(cmap = "Oranges"))
        csv = applications_by_source.to_csv(index = False).encode("utf-8")
        st.download_button("Download Data", data = csv, file_name="applications_by_source.csv", mime = "text/csv",
                           help = "Click here to download the data as CSV file")

# -- active daily loans --
active_daily_loans = dfs["vw_daily_active_loans"]
st.header("Daily Active Floating Loans Portfolio Timeline")
fig = px.line(
    active_daily_loans,
    x=active_daily_loans.columns[0],
    y=active_daily_loans.columns[1],
    width=1000,
    height=420,
)

# Customize line color, line width, and title formatting
fig.update_traces(line_color="crimson", line_width=2)
fig.update_layout(
    title_font_size=16,
    xaxis_tickangle=-45,
    margin=dict(t=50, b=50, l=50, r=50),
)
st.plotly_chart(fig, use_container_width=True)

#-- check the data out and possibly download it--
with st.expander("Daily Active Floating Loans Portfolio Timeline"):
    st.write(active_daily_loans.style.background_gradient(cmap = "RdBu"))
    csv = active_daily_loans.to_csv(index = False).encode("utf-8")
    st.download_button("Download Data", data = csv, file_name="Daily Active loans.csv", mime="text/csv",
                       help = "Click here to download the data as a CSV file")







