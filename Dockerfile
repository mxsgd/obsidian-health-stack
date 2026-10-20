FROM apache/airflow:3.3.2-python3.12
# pin airflow so pip can't up/downgrade it while resolving dbt
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" "dbt-duckdb>=1.9" "pyyaml>=6"
