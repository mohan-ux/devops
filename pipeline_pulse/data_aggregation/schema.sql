-- DDL for pipeline_runs table
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id BIGINT PRIMARY KEY,          -- Unique identifier for the workflow run (e.g., GitHub Actions Run ID)
    workflow_id BIGINT,                 -- Unique identifier for the workflow definition (e.g., GitHub Actions Workflow ID)
    workflow_name VARCHAR(255),         -- Name of the workflow (e.g., "CI Build", "Deploy to Staging")
    status VARCHAR(50),                 -- Current status of the run (e.g., queued, in_progress, completed)
    conclusion VARCHAR(50),             -- Final outcome of a completed run (e.g., success, failure, cancelled, skipped)
    event VARCHAR(100),                 -- The event that triggered the workflow run (e.g., push, pull_request, schedule, workflow_dispatch)
    branch VARCHAR(255),                -- The branch associated with the workflow run (if applicable)
    commit_sha VARCHAR(40),             -- The commit SHA that triggered the workflow run (if applicable)
    actor VARCHAR(255),                 -- The username of the user or service that initiated the run
    run_number INT,                     -- A sequential number for the run of a specific workflow
    run_attempt INT,                    -- For manually re-run workflows, this indicates the attempt number
    run_started_at TIMESTAMPTZ,         -- Timestamp indicating when the run execution actually began
    created_at TIMESTAMPTZ,             -- Timestamp indicating when the run object was created in the CI/CD system
    updated_at TIMESTAMPTZ,             -- Timestamp indicating when the run object was last modified in the CI/CD system
    duration_ms BIGINT,                 -- Total duration of the run in milliseconds (can be calculated: updated_at - run_started_at for completed runs)
    html_url VARCHAR(1024)              -- URL to view the workflow run in the CI/CD system's UI
);

-- Optional: Add indexes for frequently queried columns
-- These indexes can improve query performance when filtering or sorting by these fields.
CREATE INDEX IF NOT EXISTS idx_workflow_name ON pipeline_runs (workflow_name);
CREATE INDEX IF NOT EXISTS idx_status ON pipeline_runs (status);
CREATE INDEX IF NOT EXISTS idx_conclusion ON pipeline_runs (conclusion);
CREATE INDEX IF NOT EXISTS idx_run_started_at ON pipeline_runs (run_started_at);
CREATE INDEX IF NOT EXISTS idx_branch ON pipeline_runs (branch);
