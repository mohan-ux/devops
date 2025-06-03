import requests
import os
import json
import psycopg2
from psycopg2 import sql
from datetime import datetime, timezone

# --- Database Configuration ---
def get_db_connection_params():
    """
    Retrieves database connection parameters from environment variables.

    Returns:
        dict: Database connection parameters.
    """
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "password"),
        "dbname": os.getenv("DB_NAME", "pipeline_pulse_db")
    }

def create_table_if_not_exists(conn):
    """
    Creates the 'pipeline_runs' table and its indexes if they don't already exist.
    Reads DDL from 'schema.sql'.

    Args:
        conn: Active psycopg2 database connection.
    """
    try:
        with open("pipeline_pulse/data_aggregation/schema.sql", "r") as f:
            schema_sql = f.read()
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
        print("Successfully ensured 'pipeline_runs' table and indexes exist.")
    except FileNotFoundError:
        print("Error: 'pipeline_pulse/data_aggregation/schema.sql' not found.")
        raise
    except psycopg2.Error as db_err:
        print(f"Database error during table creation: {db_err}")
        conn.rollback() # Rollback on error
        raise

# --- GitHub API Data Fetching ---
def fetch_workflow_runs(owner, repo, token):
    """
    Fetches workflow runs for a given GitHub repository.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        token (str): GitHub Personal Access Token.

    Returns:
        dict: The JSON response from GitHub API containing workflow runs, or None if an error occurs.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}"
    }
    print(f"Fetching workflow runs from: {api_url}")
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json() # Return the full JSON response
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response content: {response.content.decode() if response.content else 'No content'}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"JSON decode error occurred: {json_err}")
        if 'response' in locals(): # Check if response variable exists
             print(f"Response content: {response.content.decode() if response.content else 'No content'}")
    return None

# --- Data Processing and Database Interaction ---
def parse_iso_datetime(datetime_str):
    """
    Parses an ISO 8601 datetime string and returns a timezone-aware datetime object (UTC).
    Returns None if parsing fails or input is None.
    """
    if not datetime_str:
        return None
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc) # Assume UTC if no timezone info
        return dt
    except (ValueError, TypeError):
        print(f"Warning: Could not parse datetime string: {datetime_str}")
        return None

def calculate_duration_ms(run_data):
    """
    Calculates the duration of a workflow run in milliseconds.
    Tries to use 'duration' field from API first (if available, assuming it's in seconds).
    Otherwise, calculates from 'run_started_at' and 'updated_at'.

    Args:
        run_data (dict): A single workflow run item from the API response.

    Returns:
        int: Duration in milliseconds, or None if not calculable.
    """
    # GitHub API sometimes provides 'duration' directly for completed runs (in seconds)
    # This information is not directly in the /runs endpoint, but let's keep for potential future use
    # if 'duration' in run_data and run_data['duration'] is not None:
    #     try:
    #         return int(float(run_data['duration']) * 1000)
    #     except (ValueError, TypeError):
    #         pass # Fall through to calculation if 'duration' is not a valid number

    run_started_at_str = run_data.get('run_started_at')
    updated_at_str = run_data.get('updated_at')

    run_started_at_dt = parse_iso_datetime(run_started_at_str)
    updated_at_dt = parse_iso_datetime(updated_at_str)

    if run_started_at_dt and updated_at_dt:
        if updated_at_dt < run_started_at_dt:
             print(f"Warning: updated_at ({updated_at_dt}) is before run_started_at ({run_started_at_dt}) for run ID {run_data.get('id')}. Duration will be 0.")
             return 0
        duration_delta = updated_at_dt - run_started_at_dt
        return int(duration_delta.total_seconds() * 1000)
    return None

def insert_workflow_run(conn, run_data):
    """
    Inserts or updates a single workflow run into the 'pipeline_runs' table.
    Uses ON CONFLICT to update if the run_id already exists.

    Args:
        conn: Active psycopg2 database connection.
        run_data (dict): A single workflow run item from the API.

    Returns:
        bool: True if insertion/update was successful, False otherwise.
    """
    duration_ms = calculate_duration_ms(run_data)

    # Safely get nested 'actor' login
    actor_data = run_data.get('actor')
    actor_login = actor_data.get('login') if isinstance(actor_data, dict) else None

    # Ensure all timestamps are parsed correctly
    run_started_at_dt = parse_iso_datetime(run_data.get('run_started_at'))
    created_at_dt = parse_iso_datetime(run_data.get('created_at'))
    updated_at_dt = parse_iso_datetime(run_data.get('updated_at'))

    insert_query = sql.SQL("""
        INSERT INTO pipeline_runs (
            run_id, workflow_id, workflow_name, status, conclusion, event,
            branch, commit_sha, actor, run_number, run_attempt,
            run_started_at, created_at, updated_at, duration_ms, html_url
        ) VALUES (
            %(run_id)s, %(workflow_id)s, %(workflow_name)s, %(status)s, %(conclusion)s, %(event)s,
            %(branch)s, %(commit_sha)s, %(actor)s, %(run_number)s, %(run_attempt)s,
            %(run_started_at)s, %(created_at)s, %(updated_at)s, %(duration_ms)s, %(html_url)s
        )
        ON CONFLICT (run_id) DO UPDATE SET
            workflow_name = EXCLUDED.workflow_name,
            status = EXCLUDED.status,
            conclusion = EXCLUDED.conclusion,
            event = EXCLUDED.event,
            branch = EXCLUDED.branch,
            commit_sha = EXCLUDED.commit_sha,
            actor = EXCLUDED.actor,
            run_number = EXCLUDED.run_number,
            run_attempt = EXCLUDED.run_attempt,
            run_started_at = EXCLUDED.run_started_at,
            updated_at = EXCLUDED.updated_at,
            duration_ms = EXCLUDED.duration_ms,
            html_url = EXCLUDED.html_url;
    """)

    run_values = {
        "run_id": run_data.get('id'),
        "workflow_id": run_data.get('workflow_id'),
        "workflow_name": run_data.get('name'),
        "status": run_data.get('status'),
        "conclusion": run_data.get('conclusion'),
        "event": run_data.get('event'),
        "branch": run_data.get('head_branch'), # Corrected from 'branch'
        "commit_sha": run_data.get('head_sha'),
        "actor": actor_login,
        "run_number": run_data.get('run_number'),
        "run_attempt": run_data.get('run_attempt'),
        "run_started_at": run_started_at_dt,
        "created_at": created_at_dt,
        "updated_at": updated_at_dt,
        "duration_ms": duration_ms,
        "html_url": run_data.get('html_url')
    }

    # Validate essential fields before attempting insert
    if not run_values["run_id"]:
        print(f"Skipping run due to missing run_id. Data: {run_data}")
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(insert_query, run_values)
        conn.commit()
        print(f"Successfully inserted/updated run ID: {run_values['run_id']}")
        return True
    except psycopg2.Error as db_err:
        print(f"Database error inserting/updating run ID {run_values['run_id']}: {db_err}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"An unexpected error occurred for run ID {run_values['run_id']}: {e}")
        conn.rollback()
        return False


# --- Main Execution ---
if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set. Cannot fetch data from GitHub.")
    else:
        github_repository = os.getenv("GITHUB_REPOSITORY")
        if github_repository:
            owner, repo = github_repository.split("/", 1)
        else:
            print("GITHUB_REPOSITORY environment variable not set. Using default: GoogleCloudPlatform/generative-ai-docs")
            owner, repo = "GoogleCloudPlatform", "generative-ai-docs"

        # Fetch data from GitHub API
        runs_data_response = fetch_workflow_runs(owner, repo, github_token)

        if runs_data_response and "workflow_runs" in runs_data_response:
            runs_list = runs_data_response["workflow_runs"]
            print(f"Successfully fetched {len(runs_list)} workflow runs for {owner}/{repo}.")

            # Database operations
            db_params = get_db_connection_params()
            conn = None
            try:
                print(f"Connecting to database '{db_params['dbname']}' at {db_params['host']}:{db_params['port']}...")
                conn = psycopg2.connect(**db_params)
                print("Successfully connected to database.")

                create_table_if_not_exists(conn) # Ensure table exists

                if not runs_list:
                    print("No workflow runs to process.")
                else:
                    successful_inserts = 0
                    failed_inserts = 0
                    for run_item in runs_list:
                        if insert_workflow_run(conn, run_item):
                            successful_inserts += 1
                        else:
                            failed_inserts += 1
                    print(f"Finished processing runs. Successful inserts/updates: {successful_inserts}, Failed: {failed_inserts}")

            except psycopg2.OperationalError as op_err:
                print(f"Database operational error: {op_err}. Check connection parameters and database server.")
            except psycopg2.Error as db_err: # Catch other psycopg2 errors
                print(f"A database error occurred: {db_err}")
            except Exception as e: # Catch any other unexpected errors
                print(f"An unexpected error occurred: {e}")
            finally:
                if conn:
                    conn.close()
                    print("Database connection closed.")
        else:
            print(f"Failed to fetch or no workflow runs found for {owner}/{repo}.")
            if runs_data_response: # If response exists but no 'workflow_runs'
                 print(f"API Response keys: {runs_data_response.keys() if isinstance(runs_data_response, dict) else 'Not a dict'}")

    print("Script finished.")
