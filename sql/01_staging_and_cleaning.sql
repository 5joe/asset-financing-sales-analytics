-- Step 1: Re-create cleaned staging table
DROP TABLE IF EXISTS "Mogo".cleaned_applications CASCADE;

CREATE TABLE "Mogo".cleaned_applications AS
SELECT 
    application_id,
    client_id,
    "application creation date" AS application_creation_date,
    "application status" AS application_status,
    "loan value" AS loan_value,
    "loan paid off at" AS loan_paid_off_at,
    "loan agent id" AS loan_agent_id,
    "loan agent" AS loan_agent,
    "loan type" AS loan_type
FROM "Mogo".applications;
