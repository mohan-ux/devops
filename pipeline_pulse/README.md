# PipelinePulse

This project aims to be a CI/CD Pipeline Visualizer & Analyzer.

## Modules

### Data Aggregation (`data_aggregation`)

This module is responsible for fetching pipeline data from various CI/CD systems and storing it in a database.

#### `fetch_github_actions_data.py`

This script fetches workflow run data from the GitHub Actions API for a specified repository and stores it in a PostgreSQL database.

**Prerequisites:**

*   Python 3.x
*   Libraries listed in `data_aggregation/requirements.txt` (install via `pip install -r data_aggregation/requirements.txt`). This includes `requests` and `psycopg2-binary`.
*   PostgreSQL server accessible to the script.

**Database Setup:**

The script requires a PostgreSQL database to store the fetched pipeline data.
*   Ensure you have a PostgreSQL server running.
*   Create a database (e.g., `pipeline_pulse_db`) that the script can connect to.
*   The necessary table (`pipeline_runs`) and indexes will be created automatically by the script if they don't exist, using the DDL statements defined in `data_aggregation/schema.sql`.

**Setup (Environment Variables):**

Configure the following environment variables before running the script:

1.  **GitHub Personal Access Token:**
    You need a GitHub Personal Access Token with the `repo` scope (or `public_repo` for public repositories) to authenticate with the GitHub API.
    ```bash
    export GITHUB_TOKEN="your_github_token_here"
    ```

2.  **Database Connection Parameters:**
    Set these to match your PostgreSQL database configuration.
    ```bash
    export DB_HOST="your_db_host"      # Defaults to 'localhost'
    export DB_PORT="5432"              # Defaults to '5432'
    export DB_USER="your_db_user"      # Defaults to 'postgres'
    export DB_PASSWORD="your_db_password"  # Defaults to 'password'
    export DB_NAME="pipeline_pulse_db"   # Defaults to 'pipeline_pulse_db'
    ```

3.  **Target Repository (Optional):**
    The script attempts to use the `GITHUB_REPOSITORY` environment variable (automatically set in GitHub Actions, e.g., `owner/repo_name`) to determine the target repository for fetching data.
    If this variable is not set, it defaults to `GoogleCloudPlatform/generative-ai-docs` for demonstration purposes. You can modify the script to change this default or pass the owner and repo as arguments if needed.

**Running the script:**

1.  Navigate to the `pipeline_pulse/data_aggregation` directory:
    ```bash
    cd pipeline_pulse/data_aggregation
    ```
2.  Ensure your environment variables are set as described above.
3.  Run the script:
    ```bash
    python fetch_github_actions_data.py
    ```

The script will fetch data from the GitHub API, attempt to connect to the database, create the table if necessary, and then insert/update the workflow run data. It will print progress and error messages to the console.
