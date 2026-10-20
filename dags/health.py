"""Daily pipeline: run.py's steps as Airflow tasks, so each one gets its own logs, retries and status.

Extracts run one after another, not in parallel: DuckDB allows a single writer process.
"""
from datetime import datetime, timedelta

from airflow.sdk import dag, task
from airflow.sdk.exceptions import AirflowSkipException

import run


@dag(schedule="0 6 * * *", start_date=datetime(2026, 10, 1), catchup=False, max_active_runs=1, tags=["health"])
def health():
    @task
    def extract_obsidian():
        run.extract_obsidian()

    # only the network call is worth retrying, a parse error fails the same way every time
    @task(retries=3, retry_delay=timedelta(minutes=5))
    def extract_fatsecret():
        if not run.extract_fatsecret():
            raise AirflowSkipException("no FATSECRET_TOKEN")

    # a skipped FatSecret still builds; a failed extract doesn't
    @task(trigger_rule="none_failed")
    def dbt_build():
        if not run.dbt_build():
            raise RuntimeError("dbt build failed, see the log above")

    extract_obsidian() >> extract_fatsecret() >> dbt_build()


health()
