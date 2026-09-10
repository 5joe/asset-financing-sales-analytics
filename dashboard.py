"""
Vehicle & Motorcycle Loan Analytics Dashboard
Run with: streamlit run dashboard.py
"""

import warnings

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from db import DEFAULT_VIEWS, fetch_views, get_db_engine

warnings.filterwarnings("ignore")

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Loan Portfolio Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Color palette (one hue family + one muted accent) ───────────
NAVY = "#1B3A5C"
BLUE_SHADES = ["#1B3A5C", "#2E5C8A", "#4A7BA6", "#7DA6C6", "#A9C6DE", "#5C6B73"]
ACCENT = "#C97B4A"  # muted terracotta, used for single-series highlight charts
TEAM_COLORS = {"Team A": "#2E5C8A", "Team B": "#C97B4A"}
PLOT_TEMPLATE = "plotly_dark"


def inject_css():
    bg, text, card = "#0E1117", "#E6E6E6", "#161B22"
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {bg}; color: {text}; }}
        div.block-container {{ padding-top: 1.5rem; }}
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
st.title("Vehicle & Motorcycle Loan Portfolio Analytics")

# ── DB connection ─────────────────────────────────────────────────
# Connection + query logic lives in db.py; here we just wrap it with
# Streamlit's caching so the engine is reused and data is cached per session.
get_engine = st.cache_resource(get_db_engine)


@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    return fetch_views(engine=get_engine(), view_names=DEFAULT_VIEWS)


# ── Helper: chart + preview/download, DRY across sections ────────
def chart_section(fig, df, title, filename, cmap="Blues", key=None):
    """Render a plotly chart, then a collapsible styled data preview with a
    CSV download button beneath it."""
    st.plotly_chart(fig, use_container_width=True, key=key)
    with st.expander(f"View & download: {title}"):
        st.dataframe(df.style.background_gradient(cmap=cmap), use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv,
            file_name=filename,
            mime="text/csv",
            key=f"dl_{key}" if key else None,
        )


# ── Sidebar ────────────────────────────────────────────────────────
# Load data at the script level (outside sidebar) so spinner shows cleanly
with st.spinner("Loading data from Postgres..."):
    dfs = load_data()

# Sidebar Layout
with st.sidebar:
    st.markdown("## 📊 Loan Analytics")
    st.caption("Loan issuance & performance reporting")

    st.divider()

    selected_page = st.radio(
        "Navigation",
        [
            "🏠 Overview",
            "👥 Team & Agent Performance",
            "💰 Loan Types & Sources",
            "📅 Timing & Volume",
        ],
        label_visibility="collapsed",
    )
    # Strip emoji for page routing
    page = selected_page.split(" ", 1)[1]

    st.divider()

    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════════
if page == "Overview":
    st.header("Loan Issuance Overview")

    df_month = dfs.get("vw_monthly_issued_loans")
    df_repeat = dfs.get("vw_repeat_clients")
    df_dal = dfs.get("vw_daily_active_loans")
    df_team = dfs.get("vw_loans_by_team")

    m1, m2, m3 = st.columns(3)
    if df_month is not None:
        m1.metric("Total Loans Issued", f"{int(df_month['loans_issued'].sum()):,}")
    if df_repeat is not None and len(df_repeat):
        m2.metric("Repeat Customers", f"{int(df_repeat.iloc[0, 0]):,}")
    if df_dal is not None and len(df_dal):
        m3.metric("Active Loans (latest)", f"{int(df_dal.iloc[-1, 1]):,}")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Loans Issued by Month")
        if df_month is not None:
            view_type = st.radio(
                "Chart type", ["Bar", "Line"], horizontal=True, key="month_view"
            )
            if view_type == "Bar":
                fig = px.bar(
                    df_month, x="month_name", y="loans_issued",
                    color_discrete_sequence=[BLUE_SHADES[1]],
                )
            else:
                fig = px.line(
                    df_month, x="month_name", y="loans_issued", markers=True,
                    color_discrete_sequence=[BLUE_SHADES[1]],
                )
            fig.update_layout(
                template=PLOT_TEMPLATE,
                xaxis=dict(title="Month", showgrid=True),
                yaxis=dict(title="Loans Issued", showgrid=True),
            )
            chart_section(fig, df_month, "Monthly Loan Issuance", "loans_by_month.csv", key="ov_month")

    with col2:
        st.subheader("Loan Issuance Breakdown by Team")
        if df_team is not None:
            fig = px.pie(
                df_team, values="loans_issued", names="final_team", hole=0.7,
                color="final_team", color_discrete_map=TEAM_COLORS,
            )
            fig.update_traces(textinfo="label+percent", textposition="outside")
            fig.update_layout(template=PLOT_TEMPLATE, showlegend=False)
            chart_section(fig, df_team, "Loan Issuance by Team", "loans_by_team.csv", cmap="Oranges", key="ov_team")

# ══════════════════════════════════════════════════════════════════
# TEAM & AGENT PERFORMANCE
# ══════════════════════════════════════════════════════════════════
elif page == "Team & Agent Performance":
    st.header("Team & Agent Performance")

    df_team = dfs.get("vw_loans_by_team")
    df_agent = dfs.get("vw_agent_issued_most_loans")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Loans Issued by Team")
        if df_team is not None:
            teams = st.multiselect(
                "Filter teams",
                options=df_team["final_team"].unique().tolist(),
                default=df_team["final_team"].unique().tolist(),
            )
            filtered_team = df_team[df_team["final_team"].isin(teams)]
            fig = px.pie(
                filtered_team, values="loans_issued", names="final_team", hole=0.6,
                color="final_team", color_discrete_map=TEAM_COLORS,
            )
            fig.update_traces(textinfo="label+percent", textposition="inside")
            fig.update_layout(template=PLOT_TEMPLATE, showlegend=True)
            chart_section(fig, filtered_team, "Loans by Team", "loans_by_team.csv", cmap="Oranges", key="tap_team")

    with col2:
        st.subheader("Loans Issued by Agent")
        if df_agent is not None:
            top_n = st.slider("Show top N agents", 3, len(df_agent), min(10, len(df_agent)))
            df_sorted = df_agent.sort_values("loans_issued_by_agent", ascending=False).head(top_n)
            df_sorted = df_sorted.sort_values("loans_issued_by_agent", ascending=True)
            fig = px.bar(
                df_sorted, x="loans_issued_by_agent", y="loan_agent_name", orientation="h",
                text="loans_issued_by_agent", color_discrete_sequence=[BLUE_SHADES[0]],
            )
            fig.update_traces(
                textposition="outside", texttemplate="%{text:,}",
                hovertemplate="<b>Agent:</b> %{y}<br><b>Loans Issued:</b> %{x:,}<extra></extra>",
            )
            fig.update_layout(
                template=PLOT_TEMPLATE,
                xaxis=dict(title="Loans Issued", showgrid=True),
                yaxis=dict(title=""),
                margin=dict(l=20, r=40, t=20, b=40),
            )
            chart_section(fig, df_sorted, "Loans by Agent", "loans_by_agent.csv", key="tap_agent")

    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        df_avg_agent = dfs.get("vw_avg_issuance_time_by_agent")
        if df_avg_agent is not None:
            st.subheader("Average Issuance Time by Agent (Monthly)")
            fig = px.line(
                df_avg_agent, x="issuance_month", y="avg_issuance_time", color="agent_name",
                markers=True,
            )
            fig.update_layout(
                template=PLOT_TEMPLATE, showlegend=True,
                xaxis=dict(title="Month"), yaxis=dict(title="Avg. Issuance Time"),
            )
            chart_section(fig, df_avg_agent, "Avg Issuance Time by Agent", "avg_issuance_time_agent.csv", key="tap_avg_agent")

    with col4:
        df_avg_team = dfs.get("vw_avg_issuance_time_by_team")
        if df_avg_team is not None:
            st.subheader("Average Issuance Time by Team (Monthly)")
            fig = px.line(
                df_avg_team, x="issuance_month", y="avg_issuance_time", color="team",
                markers=True, color_discrete_map=TEAM_COLORS,
            )
            fig.update_layout(
                template=PLOT_TEMPLATE, showlegend=True,
                xaxis=dict(title="Month"), yaxis=dict(title="Avg. Issuance Time"),
            )
            chart_section(fig, df_avg_team, "Avg Issuance Time by Team", "avg_issuance_time_team.csv", cmap="Oranges", key="tap_avg_team")

# ══════════════════════════════════════════════════════════════════
# LOAN TYPES & SOURCES
# ══════════════════════════════════════════════════════════════════
elif page == "Loan Types & Sources":
    st.header("Loan Types & Application Sources")

    col1, col2 = st.columns(2)

    with col1:
        df_plt = dfs.get("vw_popular_loan_types")
        df_plt = df_plt[df_plt["loan_type"].isin(["MOTORCYCLE", "CAR"])]
        if df_plt is not None:
            st.subheader("Popular Loan Types")
            fig = go.Figure()
            fig.add_trace(go.Pie(
                labels=df_plt["loan_type"], values=df_plt["loans_issued"],
                hole=0.7, textinfo="label+percent", textposition="outside",
                #marker=dict(colors="BLUE_SHADES", line=dict(color="#0E1117", width=2)),
                hovertemplate="<b>%{label}</b><br>Loans Issued: %{value:,}<br>Share: %{percent}<extra></extra>",
            ))
            fig.update_layout(
                template=PLOT_TEMPLATE, showlegend=False
            )
            chart_section(fig, df_plt, "Popular Loan Types", "loan_types.csv", key="lts_types")

    with col2:
        df_lr = dfs.get("vw_sales_loan_value_range")
        if df_lr is not None:
            st.subheader("Loans Issued by Value Range")
            df_lr = df_lr.copy()
            df_lr["_sort_key"] = (
                df_lr["loan_value_range"].str.split("-").str[0]
                .str.replace(",", "").str.strip().astype(float)
            )
            df_lr = df_lr.sort_values("_sort_key")
            fig = px.bar(
                df_lr, x="loan_value_range", y="loans_issued", text="loans_issued",
                color_discrete_sequence=[BLUE_SHADES[1]],
            )
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig.update_layout(
                template=PLOT_TEMPLATE,
                xaxis=dict(title="Loan Value Range", tickangle=-45, type="category"),
                yaxis=dict(title="Loans Issued", showgrid=True),
                margin=dict(l=20, r=20, t=20, b=80),
            )
            chart_section(fig, df_lr.drop(columns="_sort_key"), "Loans by Value Range", "loans_by_value_range.csv", key="lts_range")

    st.markdown("---")
    df_abs = dfs.get("vw_applications_by_source")
    if df_abs is not None:
        st.subheader("Applications & Value by Acquisition Source")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(
            name="Total Applications", x=df_abs["source"], y=df_abs["total_applications"],
            marker_color=BLUE_SHADES[0], offsetgroup=1,
            hovertemplate="<b>%{x}</b><br>Applications: %{y:,}<extra></extra>",
        ), secondary_y=False)
        fig.add_trace(go.Bar(
            name="Total Issued Value", x=df_abs["source"], y=df_abs["total_issued_value"],
            marker_color=ACCENT, offsetgroup=2,
            hovertemplate="<b>%{x}</b><br>Issued Value: %{y:,.0f}<extra></extra>",
        ), secondary_y=True)
        fig.update_layout(
            template=PLOT_TEMPLATE, barmode="group", hovermode="x unified", showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=60, b=40),
        )
        fig.update_yaxes(title_text="Total Applications", secondary_y=False, showgrid=True)
        fig.update_yaxes(title_text="Total Issued Value", secondary_y=True, showgrid=False)
        chart_section(fig, df_abs, "Applications by Source", "applications_by_source.csv", cmap="Oranges", key="lts_source")

    df_jncl = dfs.get("vw_january_non_car_loans")
    if df_jncl is not None:
        st.markdown("---")
        st.subheader("January Non-Car Loans")
        st.dataframe(df_jncl, use_container_width=True)
        csv = df_jncl.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, file_name="january_non_car_loans.csv", mime="text/csv")

# ══════════════════════════════════════════════════════════════════
# TIMING & VOLUME
# ══════════════════════════════════════════════════════════════════
elif page == "Timing & Volume":
    st.header("Timing & Active Volume")

    col1, col2 = st.columns(2)

    with col1:
        df_plw = dfs.get("vw_popular_loan_weekdays")
        df_plw = df_plw.groupby("day_of_week_num")["loans_issued"].sum().reset_index()
        if df_plw is not None:
            st.subheader("Popular Loan Weekdays")
            fig = px.bar(
                df_plw.sort_values("loans_issued", ascending=False),
                x="day_of_week_num", y="loans_issued",
                color_discrete_sequence=[BLUE_SHADES[1]],
            )
            fig.update_layout(template=PLOT_TEMPLATE, xaxis=dict(title="Day of Week (ISO)"))
            chart_section(fig, df_plw, "Popular Loan Weekdays", "popular_weekdays.csv", key="tv_weekday")

    with col2:
        df_atfc = dfs.get("vw_avg_time_first_change_to_issuance")
        if df_atfc is not None:
            st.subheader("First Status Change → Issuance")
            fig = px.line(
                df_atfc, x="issuance_month", y="avg_time_from_first_change", markers=True,
                color_discrete_sequence=[ACCENT],
            )
            fig.update_layout(template=PLOT_TEMPLATE, xaxis=dict(title="Month"), yaxis=dict(title="Avg. Time"))
            chart_section(fig, df_atfc, "First Change to Issuance", "first_change_to_issuance.csv", cmap="Oranges", key="tv_firstchange")

    df_sl = dfs.get("vw_avg_time_to_second_loan")
    if df_sl is not None and len(df_sl):
        st.metric("Avg. time between 1st and 2nd loan", str(df_sl.iloc[0, 0]))

    st.markdown("---")
    df_dal = dfs.get("vw_daily_active_loans")
    if df_dal is not None:
        st.subheader("Daily Active Loans Over Time")
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
        fig = px.line(df13, x=x_col, y=y_col)
        fig.update_traces(
            line_color=ACCENT, line_width=2,
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Active Loans: %{y:,}<extra></extra>",
        )
        fig.update_layout(
            template=PLOT_TEMPLATE, hovermode="x unified",
            xaxis=dict(title="Date", tickangle=45, showgrid=True),
            yaxis=dict(title="Active Loans", tickformat=",d", rangemode="tozero", showgrid=True),
            margin=dict(l=50, r=40, t=20, b=80),
        )
        chart_section(fig, df13, "Daily Active Loans", "daily_active_loans.csv", cmap="RdBu", key="tv_active")