
# Import libraries
import os
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

# 1. Load environment variables from the server
load_dotenv(find_dotenv(), override=True)

# 2. Build connection string from environment variables
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")

DB_PASSWORD = os.getenv("PGPASSWORD")
# Print debug info (masking password)
print("Connecting as:", DB_USER)
print("Target database:", DB_NAME)
print("Password found in .env:", "YES" if DB_PASSWORD else "NO - .env key missing or empty")

# Re-create engine with fresh credentials
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}")

# Fetch views
views = [
    "v_application",
    "v_applications",
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

dfs = {}
for view in views:
    dfs[view] = pd.read_sql(f'SELECT * FROM "Mogo".{view};', engine)
    print(f"Successfully loaded {view} ({len(dfs[view])} rows)")

print(dfs['v_applications'].head())
print(dfs['vw_monthly_issued_loans'])
print(dfs['vw_popular_loan_weekdays'])

# Lets do the visualization of the data

## Question 1 : Loans by the months
# -- line chart --
vw_monthly_issued_loans = dfs['vw_monthly_issued_loans']
# Plot
ax = vw_monthly_issued_loans.plot(
    x='month_name',
    y='loans_issued',
    label='Loans Issued',
    figsize=(10, 5)
)

# Titles & Labels
plt.title('Loans issued by the Months', fontweight='bold')
plt.xlabel('Months')
plt.ylabel('Loans Issued')
plt.legend()
plt.show()

# -- bar chart --
# plot
ax = vw_monthly_issued_loans.plot(
    x = 'month_name',
    y= 'loans_issued',
    kind = 'bar',
    figsize = (10, 5)
)
# Titles & Labels
plt.title('Loans issued by the Months', fontweight='bold')
plt.xlabel('Months')
plt.ylabel('Loans Issued')
plt.legend()
plt.show()

# -- loans by team --
print(dfs['vw_loans_by_team'])

df = dfs['vw_loans_by_team']

fig = px.pie(
    df,
    values='loans_issued',
    names='final_team',
    hole=0.80,
    width=400,
    height=400,
    color='final_team',
    color_discrete_map={'Team A': '#2a78d6', 'Team B': '#eb6834'}
)
fig.show()



# -- Agent issued most loans --
import plotly.express as px

df_ml = dfs['vw_agent_issued_most_loans']

# Sort ascending so the top agent renders at the top of the horizontal chart
df_ml_sorted = df_ml.sort_values(by='loans_issued_by_agent', ascending=True)

# Build horizontal bar chart
fig_agent = px.bar(
    df_ml_sorted,
    x='loans_issued_by_agent',
    y='loan_agent_name',
    orientation='h',
    title='<b>Loans Issued by Agents</b>',
    labels={'loans_issued_by_agent': 'Loans Issued', 'loan_agent_name': 'Agent Name'},
    text='loans_issued_by_agent'
)

fig_agent.update_traces(
    marker_color='#1e293b',
    textposition='outside',
    texttemplate='%{text:,}',  # Formats bar labels with commas (e.g., 13,014)
    hovertemplate='<b>Agent ID:</b> %{customdata}<br><b>Name:</b> %{y}<br><b>Loans Issued:</b> %{x:,}<extra></extra>',
    customdata=df_ml_sorted['loan_agent_id']
)

fig_agent.update_layout(
    template='plotly_white',
    xaxis=dict(title='Loans Issued', showgrid=True),
    yaxis=dict(title=''),
    margin=dict(l=20, r=40, t=50, b=40)
)





# -- Total repeat clients --
df_rc = dfs['vw_repeat_clients']



# -- Average time to second loan --
df_sl = dfs['vw_avg_time_to_second_loan']

# -- Popular loan weekdays --
df_plw = dfs['vw_popular_loan_weekdays']

# -- Popular loan types --
df_plt = dfs['vw_popular_loan_types']
# -- plot for this --
df_plt_cl = df_plt.iloc[:-1,:]
fig = go.Figure()

fig.add_trace(go.Pie(
    labels=df_plt_cl['loan_type'],
    values=df_plt_cl['loans_issued'],
    hole=0.5,  # Creates the donut style (set to 0 for a solid pie chart)
    textinfo='label+percent',
    textposition='inside',
    marker=dict(
        colors=['#1e293b', '#3b82f6', '#10b981', '#f59e0b', '#64748b'],  # Modern color palette
        line=dict(color='#ffffff', width=2)  # Clean slice borders
    ),
    hovertemplate='<b>Loan Type:</b> %{label}<br><b>Loans Issued:</b> %{value:,}<br><b>Share:</b> %{percent}<extra></extra>'
))

fig.update_layout(
    title='<b>Popular Loan Types Distribution</b>',
    template='plotly_white',
    margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(orientation='h', yanchor='bottom', y=-0.1, xanchor='center', x=0.5)
)





# -- Applications by source --
# with the scale handled
df_abs = dfs['vw_applications_by_source']

fig = go.Figure()

# Left Y-Axis: Total Applications (Bar)
fig.add_trace(go.Bar(
    x=df_abs['source'],
    y=df_abs['total_applications'],
    name='Total Applications',
    marker_color='#1f77b4',
    offsetgroup=1,  # Cluster position 1
    hovertemplate='<b>Source:</b> %{x}<br><b>Applications:</b> %{y:,}<extra></extra>'
))

# Right Y-Axis: Total Issued Value (Bar)
fig.add_trace(go.Bar(
    x=df_abs['source'],
    y=df_abs['total_issued_value'],
    name='Total Issued Value',
    marker_color='#2ca02c',
    yaxis='y2',     # Assign to secondary Y-axis
    offsetgroup=2,  # Cluster position 2
    hovertemplate='<b>Source:</b> %{x}<br><b>Issued Value:</b> %{y:,.2f}<extra></extra>'
))

# Layout configuration for clustered bars & dual Y-axes
fig.update_layout(
    title='<b>Total Applications and Issued Value by Source</b>',
    template='plotly_white',
    barmode='group',
    hovermode='x unified',
    showlegend=False,
    
    # Primary Y-Axis (Left)
    yaxis=dict(
        title='Total Applications',
        tickformat=',d',
        showgrid=True,
        gridcolor='#E5E5E5'
    ),
    
    # Secondary Y-Axis (Right)
    yaxis2=dict(
        title='Total Issued Value',
        tickformat=',.0f',
        overlaying='y',   # Overlay on top of the primary plot area
        side='right',     # Place axis on the right side
        showgrid=False    # Hide secondary grid lines to prevent clutter
    ),
    
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    margin=dict(t=80, b=60)
)

fig.show()




# -- January non-car loans --
df_jncl = dfs['vw_january_non_car_loans']

# -- Average issuance time by agent --  
df_aia = dfs['vw_avg_issuance_time_by_agent']

# -- Average issuance time by team --
df_ait = dfs['vw_avg_issuance_time_by_team']

# -- Average time from first change to issuance --
df_atfc = dfs['vw_avg_time_first_change_to_issuance']

# -- Daily active loans --
df_dal = dfs['vw_daily_active_loans']

# we can use a line chart to visualize the daily active loans over time
# Prepare the data 
df13 = dfs['vw_daily_active_loans'].copy()
df13.iloc[:, 0] = pd.to_datetime(df13.iloc[:,0])

x_col = df13.columns[0]
y_col = df13.columns[1]

# Create the line chart
fig = px.line(
    df13,
    x = x_col,
    y = y_col,
    title = '<b>Daily Active Loans Over Time<b>'
)

# Custom line Style and UNified hover tooltip
fig.update_traces(
    line_color='#d62728',
    line_width=2,
    hovertemplate ='<b>Date:</b> %{x|%b %d, %Y}<br><b>Active Loans:</b> %{y:,}<extra></extra>'
)

# -- Axis ticks, grids & scaling --
fig.update_layout(
    template='plotly_white',
    hovermode='x unified',

    # x-axis configuration
    xaxis=dict(
        title='Date',
        tickmode='linear',
        dtick='M1',
        tickformat='%b %Y',
        tickangle=45,
        showgrid=True,
        gridcolor='#E5E5E5',
        gridwidth=1
    ),

    # y - axis configuration
    yaxis=dict(
        title='Active Loans Count',
        tickformat=',d',
        rangemode='tozero',
        nticks=10,
        showgrid=True,
        gridcolor='#E5E5E5',
        gridwidth=1,
        zeroline=True,
        zerolinecolor='#CCCCCC',
        zerolinewidth=1.5
    ),

    margin=dict(l=50, r=40, t=60, b=80)

)

fig.show()

# plot the loan ranges here  --

df_lr = dfs['vw_sales_loan_value_range'].copy()

# Define explicit numeric order for the value ranges
range_order = [
    '1 - 1,000',
    '1,001 - 2,000',
    '2,001 - 3,000',
    '3,001 - 4,000',
    '4,001 - 5,000',
    '5,001 - 6,000',
    '6,001 - 7,000',
    '7,001 - 8,000',
    '8,001 - 9,000',
    '9,001 - 10,000'
]

# Set as categorical with explicit order and sort
df_lr['loan_value_range'] = pd.Categorical(df_lr['loan_value_range'], categories=range_order, ordered=True)
df_lr = df_lr.sort_values('loan_value_range')

fig_lr = go.Figure()

fig_lr.add_trace(go.Bar(
    x=df_lr['loan_value_range'],
    y=df_lr['loans_issued'],
    text=df_lr['loans_issued'],
    texttemplate='%{text:,}',
    textposition='outside',
    marker=dict(color='#1e293b'),  # Clean solid fill compatible with all Plotly versions
    hovertemplate='<b>Range:</b> %{x}<br><b>Loans Issued:</b> %{y:,}<extra></extra>'
))

fig_lr.update_layout(
    title='<b>Loans Issued by Value Range</b>',
    template='plotly_white',
    xaxis=dict(title='Loan Value Range', tickangle=-45),
    yaxis=dict(title='Loans Issued', showgrid=True),
    margin=dict(l=20, r=20, t=50, b=80)
)









