"""One command: extract every source into DuckDB, then dbt build (snapshots, models, tests).

    uv run run.py

Each step is its own function so the Airflow DAG (dags/health.py) runs the same code, one task per step.
"""
import os
import sys
from datetime import date
from pathlib import Path

import duckdb
from dbt.cli.main import dbtRunner

from extract import fatsecret, obsidian

ROOT = Path(__file__).parent


def load_env(path: Path = ROOT / ".env"):
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def connect() -> duckdb.DuckDBPyConnection:
    db = Path(os.environ.setdefault("DUCKDB_PATH", str(ROOT / "data" / "health.duckdb")))
    db.parent.mkdir(exist_ok=True)
    return duckdb.connect(str(db))


def extract_obsidian():
    print("extract: obsidian")
    with connect() as con:
        obsidian.run(con, Path(os.environ["JOURNAL_DIR"]))


def extract_fatsecret() -> bool:
    if not os.environ.get("FATSECRET_TOKEN"):
        print("skip fatsecret: no FATSECRET_TOKEN, run `uv run python -m extract.fatsecret` once")
        return False
    print("extract: fatsecret")
    with connect() as con:
        fatsecret.run(con, date.fromisoformat(os.environ["FATSECRET_SINCE"]))
    return True


def dbt_build() -> bool:
    dbt_dir = str(ROOT / "dbt")
    return dbtRunner().invoke(["build", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir]).success


def main() -> int:
    load_env()
    extract_obsidian()
    extract_fatsecret()
    return 0 if dbt_build() else 1


if __name__ == "__main__":
    sys.exit(main())
