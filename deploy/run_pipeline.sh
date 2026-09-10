#!/bin/bash
set -e  # Stop script execution immediately if any SQL query fails

# Automatically locate directory where this script resides
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Load Environment Variables ---
ENV_FILE="$SCRIPT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "ERROR: Environment file $ENV_FILE not found." >&2
    exit 1
fi

echo "=========================================="
echo "Starting Mogo Data Pipeline Execution"
echo "=========================================="

echo "[1/3] Running Staging & Data Cleaning..."
psql -h "$DB_HOST" -d "$DB_NAME" -U "$DB_USER" -f "$SCRIPT_DIR/01_staging_and_cleaning.sql"

echo "[2/3] Building Core Data Marts..."
psql -h "$DB_HOST" -d "$DB_NAME" -U "$DB_USER" -f "$SCRIPT_DIR/02_final_marts.sql"

echo "[3/3] Updating Reporting Views..."
psql -h "$DB_HOST" -d "$DB_NAME" -U "$DB_USER" -f "$SCRIPT_DIR/03_reporting_views.sql"

echo "=========================================="
echo "Pipeline Run Completed Successfully!"
echo "=========================================="