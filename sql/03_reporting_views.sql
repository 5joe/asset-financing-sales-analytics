-- Q1: Monthly Loans Issued
CREATE OR REPLACE VIEW "Mogo".vw_monthly_issued_loans AS
SELECT
    COUNT(application_id) AS loans_issued,
    EXTRACT(MONTH FROM CAST(application_creation_date AS DATE)) AS month_of_creation,
    TO_CHAR(CAST(application_creation_date AS DATE), 'Month') AS month_name
FROM "Mogo".final_applications
GROUP BY 2, 3
ORDER BY month_of_creation ASC;

-- select * from "Mogo".vw_monthly_issued_loans;

-- Q2: Loans Issued by Team
CREATE OR REPLACE VIEW "Mogo".vw_loans_by_team AS
SELECT 
    COUNT(fa.application_id) AS loans_issued,
    CASE 
        WHEN fa.loan_agent_id = 3 THEN 
            CASE 
                WHEN fa.application_creation_date::timestamp < '2025-03-01 08:32:00'::timestamp THEN 'Team A'
                ELSE 'Team B'
            END
        ELSE (
            SELECT utc.team
            FROM "Mogo".user_team_changes utc
            WHERE utc.agent_id = fa.loan_agent_id
            ORDER BY utc.team_changed_at DESC
            LIMIT 1
        )
    END AS final_team
FROM "Mogo".final_applications AS fa
GROUP BY 2;
-- select * from "Mogo".vw_loans_by_team;

-- 3. which loan agent issued the most loans? --
CREATE OR REPLACE VIEW "Mogo".vw_agent_issued_most_loans AS
select 
	count(application_id) as loans_issued_by_agent,
	loan_agent_id,
	case loan_agent_id
		when 1 then 'John'
		when 2 then 'Susan'
		when 3 then 'Peter'
		when 4 then 'Mary'
		else 'error'
	end as loan_agent_name
from "Mogo".final_applications
group by loan_agent_id
order by loans_issued_by_agent DESC;
-- limit 1;

-- SELECT * FROM "Mogo".vw_agent_issued_most_loans;

-- 4. please breakdown sales by loan value (in 1k ranges) --
CREATE OR REPLACE VIEW "Mogo".vw_sales_loan_value_range AS
select 
	case 
		when loan_value	between 1 and 1000 then '1 - 1,000'
		when loan_value	between 1001 and 2000 then '1,001 - 2,000'
		when loan_value	between 2001 and 3000 then '2,001 - 3,000'
		when loan_value	between 3001 and 4000 then '3,001 - 4,000'
		when loan_value	between 4001 and 5000 then '4,001 - 5,000'
		when loan_value	between 5001 and 6000 then '5,001 - 6,000'
		when loan_value	between 6001 and 7000 then '6,001 - 7,000'
		when loan_value	between 7001 and 8000 then '7,001 - 8,000'
		when loan_value	between 8001 and 9000 then '8,001 - 9,000'
		when loan_value	between 9001 and 10000 then '9,001 - 10,000'
		else 'Above 10k'
	end as loan_value_range,
	count(application_id) as loans_issued
from "Mogo".final_applications
	group by 1
	order by loans_issued desc;

-- SELECT * FROM "Mogo".vw_sales_loan_value_range;

-- Q5: Repeat Clients Summary
CREATE OR REPLACE VIEW "Mogo".vw_repeat_clients AS
WITH repeat_clients AS (
    SELECT client_id
    FROM "Mogo".final_applications
    GROUP BY client_id
    HAVING COUNT(client_id) >= 2
)
SELECT COUNT(*) AS total_repeat_customers FROM repeat_clients;

-- select * from "Mogo".vw_repeat_clients;

-- Q6: Average Time Between Payout and Second Loan
CREATE OR REPLACE VIEW "Mogo".vw_avg_time_to_second_loan AS
WITH client_timeline AS (
    SELECT 
        a.client_id,
        s.status_changed_at::timestamp AS payout_time,
        ROW_NUMBER() OVER(PARTITION BY a.client_id ORDER BY s.status_changed_at) AS seq
    FROM "Mogo".applications_status_changes s
    JOIN "Mogo".final_applications a ON s.application_id = a.application_id
    WHERE s.status = 5
)
SELECT 
    AVG(t2.payout_time - t1.payout_time) AS avg_time_to_second_loan
FROM client_timeline t1
JOIN client_timeline t2 ON t1.client_id = t2.client_id AND t1.seq = 1 AND t2.seq = 2;

-- select * from "Mogo".vw_avg_time_to_second_loan;

-- Q7: Most Popular Weekdays for Loan Issuance
CREATE OR REPLACE VIEW "Mogo".vw_popular_loan_weekdays AS
SELECT 
    EXTRACT(DAY FROM CAST(status_changed_at AS date)) AS weekday,
    EXTRACT(ISODOW FROM CAST(status_changed_at AS date)) AS day_of_week_num,
    COUNT(DISTINCT application_id) AS loans_issued
FROM "Mogo".applications_status_changes
WHERE status = 5
GROUP BY 1, 2
ORDER BY loans_issued DESC;

-- SELECT * FROM "Mogo".vw_popular_loan_weekdays;

-- Q8: Most Popular Loan Types
CREATE OR REPLACE VIEW "Mogo".vw_popular_loan_types AS
SELECT 
    COALESCE(NULLIF(TRIM(a.loan_type), ''), 'UNSPECIFIED') AS loan_type,
    COUNT(DISTINCT s.application_id) AS loans_issued
FROM "Mogo".applications_status_changes s
JOIN "Mogo".final_applications a ON s.application_id = a.application_id
WHERE s.status = 5
GROUP BY 1
ORDER BY loans_issued DESC;

-- select * from "Mogo".vw_popular_loan_types;

-- Q9: Applications and Value Generated per Source Channel
CREATE OR REPLACE VIEW "Mogo".vw_applications_by_source AS
SELECT 
    COALESCE(sl.source_label, 'Direct / Organic Traffic') AS source,
    COUNT(DISTINCT a.application_id) AS total_applications,
    SUM(CASE WHEN s.status = 5 THEN COALESCE(a.loan_value, 0) ELSE 0 END) AS total_issued_value
FROM "Mogo".final_applications a
LEFT JOIN "Mogo".source_label sl ON a.application_id = sl.application_id
LEFT JOIN "Mogo".applications_status_changes s ON a.application_id = s.application_id AND s.status = 5
GROUP BY 1
ORDER BY total_issued_value DESC;

-- select * from "Mogo".vw_applications_by_source;

-- Q10: Non-Car January Loans Summary
CREATE OR REPLACE VIEW "Mogo".vw_january_non_car_loans AS
SELECT 
    a.application_id, 
    a.client_id, 
    COALESCE(a.loan_value, 0) AS loan_value, 
    COALESCE(NULLIF(TRIM(a.loan_type), ''), 'UNSPECIFIED') AS loan_type, 
    s.status_changed_at AS issued_at
FROM "Mogo".applications_status_changes s
JOIN "Mogo".final_applications a ON s.application_id = a.application_id
WHERE s.status = 5 
  AND COALESCE(a.loan_type, '') != 'CAR'
  AND EXTRACT(MONTH FROM CAST(s.status_changed_at AS date)) = 1;

-- select * from "Mogo".vw_january_non_car_loans;

-- Q11A: Average Issuance Time Monthly by Agent
CREATE OR REPLACE VIEW "Mogo".vw_avg_issuance_time_by_agent AS
SELECT 
    TO_CHAR(CAST(s.status_changed_at AS date), 'YYYY-MM') AS issuance_month,
    COALESCE(NULLIF(TRIM(a.loan_agent), ''), 'Unassigned / Automated System') AS agent_name,
    AVG(CAST(s.status_changed_at AS date) - CAST(a.application_creation_date AS date)) AS avg_issuance_time
FROM "Mogo".applications_status_changes s
JOIN "Mogo".final_applications a ON s.application_id = a.application_id
WHERE s.status = 5
GROUP BY 1, 2
ORDER BY issuance_month ASC;

-- select * from "Mogo".vw_avg_issuance_time_by_agent;

-- Q11B: Average Issuance Time Monthly by Team
CREATE OR REPLACE VIEW "Mogo".vw_avg_issuance_time_by_team AS
WITH latest_agent_team AS (
    SELECT DISTINCT ON (agent_id) agent_id, team
    FROM "Mogo".user_team_changes
    ORDER BY agent_id, team_changed_at DESC
)
SELECT 
    TO_CHAR(CAST(s.status_changed_at AS date), 'YYYY-MM') AS issuance_month,
    t.team,
    AVG(CAST(s.status_changed_at AS date) - CAST(a.application_creation_date AS date)) AS avg_issuance_time
FROM "Mogo".applications_status_changes s
JOIN "Mogo".final_applications a ON s.application_id = a.application_id
JOIN latest_agent_team t ON a.loan_agent_id = t.agent_id
WHERE s.status = 5
GROUP BY 1, 2
ORDER BY issuance_month ASC;
-- select * from "Mogo".vw_avg_issuance_time_by_team;

-- Q12: Average Time from First Status Change to Final Issuance
CREATE OR REPLACE VIEW "Mogo".vw_avg_time_first_change_to_issuance AS
WITH first_status_change AS (
    SELECT application_id, MIN(CAST(status_changed_at AS date)) AS first_change_time
    FROM "Mogo".applications_status_changes
    GROUP BY application_id
)
SELECT 
    TO_CHAR(CAST(s.status_changed_at AS date), 'YYYY-MM') AS issuance_month,
    AVG(CAST(s.status_changed_at AS date) - CAST(f.first_change_time AS date)) AS avg_time_from_first_change
FROM "Mogo".applications_status_changes s
JOIN first_status_change f ON s.application_id = f.application_id
WHERE s.status = 5
GROUP BY 1
ORDER BY issuance_month ASC;

-- select * from "Mogo".vw_avg_time_first_change_to_issuance;

-- Q13: Daily Active Loans Timeline
CREATE OR REPLACE VIEW "Mogo".vw_daily_active_loans AS
WITH daily_volume_changes AS (
    SELECT 
        "application_creation_date"::date AS transaction_date,
        COUNT(*) AS loan_additions,
        0 AS loan_subtractions
    FROM "Mogo".final_applications
    GROUP BY 1

    UNION ALL

    SELECT 
        ("status_changed_at"::date + INTERVAL '1 day')::date AS transaction_date,
        0 AS loan_additions,
        COUNT(*) AS loan_subtractions
    FROM "Mogo".applications_status_changes
    WHERE "status" = 6
    GROUP BY 1
),
net_daily_changes AS (
    SELECT 
        transaction_date,
        SUM(loan_additions) - SUM(loan_subtractions) AS net_change
    FROM daily_volume_changes
    WHERE transaction_date IS NOT NULL
    GROUP BY 1
),
running_timeline AS (
    SELECT 
        transaction_date,
        SUM(net_change) OVER (ORDER BY transaction_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS active_loans_count
    FROM net_daily_changes
),
calendar AS (
    SELECT day::date AS check_date
    FROM generate_series(
        (SELECT MIN(transaction_date) FROM running_timeline),
        CURRENT_DATE,
        INTERVAL '1 day'
    ) day
)
SELECT 
    c.check_date,
    COALESCE(
        (SELECT r.active_loans_count 
         FROM running_timeline r 
         WHERE r.transaction_date <= c.check_date 
         ORDER BY r.transaction_date DESC LIMIT 1), 
        0
    ) AS active_loans_count
FROM calendar c
ORDER BY c.check_date;

-- select * from "Mogo".vw_daily_active_loans;