"""One command: extract every source into DuckDB, then dbt build (snapshots, models, tests).

    uv run run.py
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


def main() -> int:
    load_env()
    db = Path(os.environ.setdefault("DUCKDB_PATH", str(ROOT / "data" / "health.duckdb")))
    db.parent.mkdir(exist_ok=True)

    print("extract: obsidian")
    with duckdb.connect(str(db)) as con:
        obsidian.run(con, Path(os.environ["JOURNAL_DIR"]))
        if os.environ.get("FATSECRET_TOKEN"):
            print("extract: fatsecret")
            fatsecret.run(con, date.fromisoformat(os.environ["FATSECRET_SINCE"]))
        else:
            print("skip fatsecret: no FATSECRET_TOKEN, run `uv run python -m extract.fatsecret` once")

    dbt_dir = str(ROOT / "dbt")
    result = dbtRunner().invoke(["build", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir])
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
