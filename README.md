# Asset Financing Sales Analytics

Sales/portfolio analysis for a vehicle & motorbike loan business (schema: `Mogo` in Postgres). Raw application data gets cleaned up in SQL, then queried to answer 13 business questions issuance trends, agent and team performance, repeat borrowers, channel value, and more across 14 reporting views. A multi-page Streamlit dashboard reads the results and renders them with Plotly.

## Pipeline

Three SQL scripts, run in order (orchestrated by `run_pipeline.sh`, scheduled nightly via cron):

1. **`01_staging_and_cleaning.sql`:** pulls the raw `applications` table into `cleaned_applications`, renaming the messy quoted column names (`"application creation date"`, `"loan agent"`, etc.) into normal snake_case.
2. **`02_final_marts.sql`:** builds `final_applications`, the table everything downstream reads from. Also where a couple of data-quality patches happen: agent IDs 1–4 get mapped to real names (John, Susan, Peter, Mary), and blank/null loan types get set to `'NA'`.
3. **`03_reporting_views.sql`:** creates 14 views answering the 13 business questions (one question, #11, gets split into an agent-level and a team-level view), using window functions, running totals, and a few multi-step CTEs.

It's a full drop-and-rebuild pipeline: `02_final_marts.sql` does a `DROP ... CASCADE` on the base table, so every downstream view gets cascade-dropped and has to be explicitly recreated by `03_` on each run.

`db.py` loads all 14 views into pandas DataFrames, and `dashboard.py` (Streamlit) renders them.

## The 14 views

| #   | View                                     | What it answers                                                                                                         |
| --- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 1   | `vw_monthly_issued_loans`              | Loans issued per month                                                                                                  |
| 2   | `vw_loans_by_team`                     | Loans issued by team (handles a mid-2025 team reassignment for one agent, plus a team-history lookup for everyone else) |
| 3   | `vw_agent_issued_most_loans`           | Which agent issued the most loans                                                                                       |
| 4   | `vw_sales_loan_value_range`            | Loan volume broken down into $1k value bands                                                                            |
| 5   | `vw_repeat_clients`                    | Count of clients with 2+ loans                                                                                          |
| 6   | `vw_avg_time_to_second_loan`           | Average gap between a client's 1st and 2nd payout                                                                       |
| 7   | `vw_popular_loan_weekdays`             | Which days of the week loans get issued most                                                                            |
| 8   | `vw_popular_loan_types`                | Most popular loan types                                                                                                 |
| 9   | `vw_applications_by_source`            | Applications and $ value issued, broken down by acquisition source                                                      |
| 10  | `vw_january_non_car_loans`             | Non-car loans issued in January                                                                                         |
| 11a | `vw_avg_issuance_time_by_agent`        | Avg. time from application to issuance, by month + agent                                                                |
| 11b | `vw_avg_issuance_time_by_team`         | Same, but by team instead of agent                                                                                      |
| 12  | `vw_avg_time_first_change_to_issuance` | Avg. time from an application's first status change to final issuance                                                   |
| 13  | `vw_daily_active_loans`                | Running daily count of active loans (additions minus payoffs, walked forward day by day)                                |

Status code `5` = loan issued/paid out, `6` = loan closed both come from `applications_status_changes`.

## Dashboard

Streamlit app, 4 pages (Overview / Team & Agent Performance / Loan Types & Sources / Timing & Volume), with:

- Filters — team multiselect, top-N agent slider, line/bar toggle, date-range slider on the active-loans timeline
- KPI cards — total loans issued, repeat customers, current active loan count
- A restrained dark-mode design system: one blue-tone palette plus a single terracotta accent for two-way contrasts, `plotly_dark` templates on every chart, theme set at the Streamlit framework level via `.streamlit/config.toml`
- All 14 views loaded through a single reused connection instead of opening/closing one per query

## Getting it running

1. Clone and install:

   ```bash
   git clone https://github.com/5joe/asset-financing-sales-analytics.git
   cd asset-financing-sales-analytics
   pip install -r requirements.txt
   ```
2. Set your Postgres connection as environment variables (a `.env` file works, `db.py` loads it automatically):

   ```
   DB_USER=appuser
   PGPASSWORD=your_password
   DB_HOST=127.0.0.1
   DB_PORT=5432
   DB_NAME=appdb
   DB_SCHEMA=Mogo
   ```

   All of these have defaults except `PGPASSWORD` — see `get_db_engine()` in `db.py`. Note `DB_HOST=127.0.0.1` only works if you're running against a local Postgres — pointing at a remote one needs its actual address (see below, this one cost me a couple hours).
3. Run the three SQL scripts in order against a database that has the `Mogo` schema's raw tables (`applications`, `applications_status_changes`, `user_team_changes`, `source_label`).
4. Launch the dashboard:

   ```bash
   streamlit run dashboard.py
   ```

## Data Access

The database this project queries lives on a private VPS, not a public endpoint. There's no public connection string to plug in access is locked down at the network level (Postgres config, DB-level ACLs, and infrastructure firewall rules), separate from anything in this repo. If you need access for review purposes, reach out directly rather than trying to point `db.py` at it.

## Problems I ran into (and how I debugged them)

This started life as a broken pipeline: a Python script that couldn't connect to Postgres at all and getting it to a working, scheduled ETL feeding a live dashboard meant doing the DB admin and networking work myself, not just the analytics.

**"Password authentication failed" wasn't actually an auth problem.** The password was correct confirmed by connecting with the same credentials directly on the server. The real issue was `DB_HOST=127.0.0.1` in the `.env` file: that resolves to "this machine" wherever the connection originates from. On the server, that's Postgres. From my laptop, it's just my laptop. Swapped it for the server's actual address.

**That fix uncovered a real timeout, which turned out to be three separate blockers stacked on top of each other** each one independently capable of killing the connection, and each requiring a different diagnostic approach:

- **Postgres itself** wasn't listening on anything but localhost (`listen_addresses` in `postgresql.conf`). Fixed and confirmed with `ss -tlnp` that it moved from binding `127.0.0.1:5432` to `0.0.0.0:5432`.
- **Postgres's own access list** (`pg_hba.conf`) is separate from anything OS-level had to explicitly authorize the connecting IP there too. Hit a config typo along the way (missing CIDR suffix) that took the whole service down; traced it through `journalctl` and the Postgres logs, and learned to always check `systemctl status` after a config change instead of assuming a reload worked.
- **The VPS provider's own cloud-level firewall**, sitting in front of the server entirely outside SSH reach. Ruled out the OS firewall first (`iptables -L -n` was wide open), then used an external port-checking tool to confirm port 5432 was closed from the outside which is what pointed at the cloud firewall as the actual remaining blocker. Added an explicit allow rule there, ordered correctly above the default deny-all.

Working through all three in sequence : app config → database ACL → infrastructure firewall was the part of this project that had the steepest part of the project that I had to navigate and workout.

**Case-sensitive schema names.** Queries were failing with "relation does not exist" even though the views clearly existed. Turned out the schema had been created as `"Mogo"` (quoted, mixed-case), which Postgres treats as case-sensitive and doesn't include in the default search path. Fixed the queries to schema-qualify explicitly, then set a persistent default (`ALTER ROLE ... SET search_path`) so future connections wouldn't need to.

**Pipeline drift.** At one point the views actually in the database didn't match what the current SQL files defined. Root cause: the SQL had been edited after the last scheduled run, and since this is a full drop-and-rebuild pipeline, the database was still reflecting the older script version until the next run caught up. Diagnosed by comparing what's actually in the DB, what the current script defines, and what the last pipeline log said ran — then manually re-triggered the pipeline instead of waiting for the next scheduled run.

## Stack

- **PostgreSQL:** CTEs, window functions, running totals, role-level `search_path`
- **Python:** pandas, SQLAlchemy, psycopg2, python-dotenv
- **Plotly:** charts (dual-axis bars, donut charts, custom hover templates, correctly-ordered bucketed ranges)
- **Streamlit:** multi-page dashboard, caching, dark theme

## Notes / known quirks

- Agent names for IDs 1–4 are hardcoded (`John`, `Susan`, `Peter`, `Mary`) rather than pulled from a real agents table.
- View 2's team logic has a manual carve-out for a specific agent around a March 2025 cutoff worth revisiting if that agent's history changes again.
- `db.py` swallows per-view load failures (prints and skips) rather than raising, so a broken view won't crash the whole dashboard check stdout if a chart looks empty.
