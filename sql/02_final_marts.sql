-- Step 2: Build final application dimension table
DROP TABLE IF EXISTS "Mogo".final_applications CASCADE;

CREATE TABLE "Mogo".final_applications AS
SELECT 
    application_id,
    client_id,
    application_creation_date,
    application_status,
    loan_value,
    loan_paid_off_at,
    loan_agent_id,
    CASE loan_agent_id
        WHEN 1 THEN 'John'
        WHEN 2 THEN 'Susan'
        WHEN 3 THEN 'Peter'
        WHEN 4 THEN 'Mary'
        ELSE loan_agent
    END AS loan_agent,
    CASE
        WHEN loan_type IS NULL OR TRIM(loan_type) = '' OR TRIM(loan_type) = ' '
        THEN 'NA'
        ELSE loan_type
    END AS loan_type
FROM "Mogo".cleaned_applications;
