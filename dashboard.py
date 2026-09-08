"""
Mogo Loan Analytics Dashboard
Run with: streamlit run dashboard.py
"""

import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Mogo Loan Analytics",
    page_icon="\U0001F4CA",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Restrained color palette (one hue family + one muted accent) ──
NAVY = "#1B3A5C"
BLUE_SHADES = ["#1B3A5C", "#2E5C8A", "#4A7BA6", "#7DA6C6", "#A9C6DE", "#5C6B73"]
ACCENT = "#C97B4A"          # muted terracotta — used only for 2-way contrasts
TEAM_COLORS = {"Team A": "#2E5C8A", "Team B": "#C97B4A"}
GRID = "#E5E5E5"

# ── Theme: dark mode ────────────────────────────────────────────
st.session_state.theme = "Dark"


def plot_template():
    return "plotly_dark"


def inject_css():
    bg, text, card = "#0E1117", "#E6E6E6", "#161B22"
    st.markdown(
        f"""
        <style>
            .stApp {{ background-color: {bg}; color: {text}; }}
            section[data-testid="stSidebar"] {{
                background-color: {card};
                border-right: 1px solid #2A2F3A;
            }}
            div[data-testid="stMetric"] {{
                background-color: {card};
                padding: 14px 16px;
                border-radius: 10px;
                border: 1px solid #2A2F3A;
            }}
            h1, h2, h3 {{ color: #7DA6C6; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()

# ── DB connection ──────────────────────────────────────────────
load_dotenv(find_dotenv(), override=True)

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
    "vw_daily_active_loans",
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


# ── Sidebar ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## \U0001F4CA Mogo Analytics")
    st.caption("Loan issuance & performance reporting")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "\U0001F3E0  Overview",
            "\U0001F465  Team & Agent Performance",
            "\U0001F4B0  Loan Types & Sources",
            "\U0001F4C5  Timing & Volume",
        ],
        label_visibility="collapsed",
    )
    page = page.split("  ", 1)[1]

    st.markdown("---")

    if st.button("\U0001F504 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    with st.spinner("Loading data from Postgres..."):
        dfs = load_data()
    st.caption(f"{len(dfs)} views loaded")

TPL = plot_template()


# ══════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("Loan Issuance Overview")

    df_month = dfs.get("vw_monthly_issued_loans")
    df_repeat = dfs.get("vw_repeat_clients")
    df_dal = dfs.get("vw_daily_active_loans")

    col1, col2, col3 = st.columns(3)
    if df_month is not None:
        col1.metric("Total Loans Issued", f"{int(df_month['loans_issued'].sum()):,}")
    if df_repeat is not None and len(df_repeat):
        col2.metric("Repeat Customers", f"{int(df_repeat['total_repeat_customers'].iloc[0]):,}")
    if df_dal is not None and len(df_dal):
        col3.metric("Active Loans (latest)", f"{int(df_dal.iloc[-1, 1]):,}")

    st.markdown("### Loans Issued by Month")
    if df_month is not None:
        view_type = st.radio("Chart type", ["Line", "Bar"], horizontal=True, key="month_view")
        if view_type == "Line":
            fig = px.line(df_month, x="month_name", y="loans_issued", markers=True,
                          title="Loans Issued by Month", color_discrete_sequence=[BLUE_SHADES[1]])
        else:
            fig = px.bar(df_month, x="month_name", y="loans_issued",
                         title="Loans Issued by Month", color_discrete_sequence=[BLUE_SHADES[1]])
        fig.update_layout(template=TPL)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Team Split")
    df_team = dfs.get("vw_loans_by_team")
    if df_team is not None:
        fig = px.pie(
            df_team, values="loans_issued", names="final_team", hole=0.6,
            color="final_team", color_discrete_map=TEAM_COLORS,
        )
        fig.update_layout(template=TPL)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# TEAM & AGENT PERFORMANCE
# ══════════════════════════════════════════════════════════════
elif page == "Team & Agent Performance":
    st.title("Team & Agent Performance")

    df_team = dfs.get("vw_loans_by_team")
    if df_team is not None:
        st.markdown("### Loans Issued by Team")
        teams = st.multiselect(
            "Filter teams", options=df_team["final_team"].unique().tolist(),
            default=df_team["final_team"].unique().tolist(),
        )
        filtered = df_team[df_team["final_team"].isin(teams)]
        fig = px.pie(
            filtered, values="loans_issued", names="final_team", hole=0.6,
            color="final_team", color_discrete_map=TEAM_COLORS,
        )
        fig.update_layout(template=TPL)
        st.plotly_chart(fig, use_container_width=True)

    df_agent = dfs.get("vw_agent_issued_most_loans")
    if df_agent is not None:
        st.markdown("### Loans Issued by Agent")
        top_n = st.slider("Show top N agents", 3, len(df_agent), min(10, len(df_agent)))
        df_sorted = df_agent.sort_values("loans_issued_by_agent", ascending=False).head(top_n)
        df_sorted = df_sorted.sort_values("loans_issued_by_agent", ascending=True)

        fig = px.bar(
            df_sorted, x="loans_issued_by_agent", y="loan_agent_name", orientation="h",
            title="Loans Issued by Agent", text="loans_issued_by_agent",
        )
        fig.update_traces(
            marker_color=BLUE_SHADES[0], textposition="outside",
            texttemplate="%{text:,}",
            hovertemplate="<b>Agent ID:</b> %{customdata}<br><b>Name:</b> %{y}<br><b>Loans Issued:</b> %{x:,}<extra></extra>",
            customdata=df_sorted["loan_agent_id"] if "loan_agent_id" in df_sorted else None,
        )
        fig.update_layout(
            template=TPL,
            xaxis=dict(title="Loans Issued", showgrid=True),
            yaxis=dict(title=""),
            margin=dict(l=20, r=40, t=50, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    df_avg_agent = dfs.get("vw_avg_issuance_time_by_agent")
    if df_avg_agent is not None:
        st.markdown("### Average Issuance Time by Agent (Monthly)")
        st.dataframe(df_avg_agent, use_container_width=True)

    df_avg_team = dfs.get("vw_avg_issuance_time_by_team")
    if df_avg_team is not None:
        st.markdown("### Average Issuance Time by Team (Monthly)")
        fig = px.line(
            df_avg_team, x="issuance_month", y="avg_issuance_time", color="team",
            markers=True, title="Average Issuance Time by Team",
            color_discrete_map=TEAM_COLORS,
        )
        fig.update_layout(template=TPL)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# LOAN TYPES & SOURCES
# ══════════════════════════════════════════════════════════════
elif page == "Loan Types & Sources":
    st.title("Loan Types & Application Sources")

    df_plt = dfs.get("vw_popular_loan_types")
    if df_plt is not None:
        st.markdown("### Popular Loan Types")
        df_plt_cl = df_plt.iloc[:-1, :] if len(df_plt) > 1 else df_plt
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=df_plt_cl["loan_type"], values=df_plt_cl["loans_issued"],
            hole=0.5, textinfo="label+percent", textposition="inside",
            marker=dict(colors=BLUE_SHADES, line=dict(color="#ffffff", width=2)),
            hovertemplate="<b>Loan Type:</b> %{label}<br><b>Loans Issued:</b> %{value:,}<br><b>Share:</b> %{percent}<extra></extra>",
        ))
        fig.update_layout(
            title="Popular Loan Types Distribution", template=TPL,
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)

    df_lr = dfs.get("vw_sales_loan_value_range")
    if df_lr is not None:
        st.markdown("### Loans Issued by Value Range")
        df_lr = df_lr.copy()
        # Sort ranges numerically by their lower bound (e.g. "1,001 - 2,000" -> 1001)
        df_lr["_sort_key"] = (
            df_lr["loan_value_range"].str.split("-").str[0].str.replace(",", "").str.strip().astype(float)
        )
        df_lr = df_lr.sort_values("_sort_key")

        fig_lr = go.Figure()
        fig_lr.add_trace(go.Bar(
            x=df_lr["loan_value_range"], y=df_lr["loans_issued"],
            text=df_lr["loans_issued"], texttemplate="%{text:,}", textposition="outside",
            marker=dict(color=BLUE_SHADES[1]),
            hovertemplate="<b>Range:</b> %{x}<br><b>Loans Issued:</b> %{y:,}<extra></extra>",
        ))
        fig_lr.update_layout(
            title="Loans Issued by Value Range", template=TPL,
            xaxis=dict(title="Loan Value Range", tickangle=-45, type="category"),
            yaxis=dict(title="Loans Issued", showgrid=True),
            margin=dict(l=20, r=20, t=50, b=80),
        )
        st.plotly_chart(fig_lr, use_container_width=True)

    df_abs = dfs.get("vw_applications_by_source")
    if df_abs is not None:
        st.markdown("### Applications & Value by Source")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_abs["source"], y=df_abs["total_applications"], name="Total Applications",
            marker_color=BLUE_SHADES[0], offsetgroup=1,
            hovertemplate="<b>Source:</b> %{x}<br><b>Applications:</b> %{y:,}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=df_abs["source"], y=df_abs["total_issued_value"], name="Total Issued Value",
            marker_color=BLUE_SHADES[3], yaxis="y2", offsetgroup=2,
            hovertemplate="<b>Source:</b> %{x}<br><b>Issued Value:</b> %{y:,.2f}<extra></extra>",
        ))
        fig.update_layout(
            title="Total Applications and Issued Value by Source", template=TPL,
            barmode="group", hovermode="x unified",
            yaxis=dict(title="Total Applications", tickformat=",d", showgrid=True),
            yaxis2=dict(title="Total Issued Value", tickformat=",.0f", overlaying="y",
                        side="right", showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=80, b=60),
        )
        st.plotly_chart(fig, use_container_width=True)

    df_jncl = dfs.get("vw_january_non_car_loans")
    if df_jncl is not None:
        st.markdown("### January Non-Car Loans")
        st.dataframe(df_jncl, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# TIMING & VOLUME
# ══════════════════════════════════════════════════════════════
elif page == "Timing & Volume":
    st.title("Timing & Active Volume")

    df_plw = dfs.get("vw_popular_loan_weekdays")
    if df_plw is not None:
        st.markdown("### Popular Loan Weekdays")
        fig = px.bar(
            df_plw.sort_values("loans_issued", ascending=False),
            x="day_of_week_num", y="loans_issued",
            title="Loans Issued by Day of Week", color_discrete_sequence=[BLUE_SHADES[1]],
        )
        fig.update_layout(template=TPL, xaxis=dict(title="Day of Week (ISO)"))
        st.plotly_chart(fig, use_container_width=True)

    df_sl = dfs.get("vw_avg_time_to_second_loan")
    if df_sl is not None and len(df_sl):
        st.markdown("### Average Time to Second Loan")
        st.metric("Avg. time between 1st and 2nd loan", str(df_sl.iloc[0, 0]))

    df_atfc = dfs.get("vw_avg_time_first_change_to_issuance")
    if df_atfc is not None:
        st.markdown("### Average Time: First Status Change → Issuance")
        fig = px.line(
            df_atfc, x="issuance_month", y="avg_time_from_first_change", markers=True,
            title="Avg Time from First Change to Issuance",
            color_discrete_sequence=[BLUE_SHADES[2]],
        )
        fig.update_layout(template=TPL)
        st.plotly_chart(fig, use_container_width=True)

    df_dal = dfs.get("vw_daily_active_loans")
    if df_dal is not None:
        st.markdown("### Daily Active Loans Over Time")
        df13 = df_dal.copy()
        x_col, y_col = df13.columns[0], df13.columns[1]
        df13[x_col] = pd.to_datetime(df13[x_col])

        date_range = st.slider(
            "Date range",
            min_value=df13[x_col].min().to_pydatetime(),
            max_value=df13[x_col].max().to_pydatetime(),
            value=(df13[x_col].min().to_pydatetime(), df13[x_col].max().to_pydatetime()),
        )
        mask = (df13[x_col] >= date_range[0]) & (df13[x_col] <= date_range[1])
        df13 = df13[mask]

        fig = px.line(df13, x=x_col, y=y_col, title="Daily Active Loans Over Time")
        fig.update_traces(
            line_color=ACCENT, line_width=2,
            hovertemplate="<b>Date:</b> %{x|%b %d, %Y}<br><b>Active Loans:</b> %{y:,}<extra></extra>",
        )
        fig.update_layout(
            template=TPL, hovermode="x unified",
            xaxis=dict(title="Date", tickangle=45, showgrid=True),
            yaxis=dict(title="Active Loans Count", tickformat=",d", rangemode="tozero",
                      showgrid=True, zeroline=True),
            margin=dict(l=50, r=40, t=60, b=80),
        )
        st.plotly_chart(fig, use_container_width=True)
