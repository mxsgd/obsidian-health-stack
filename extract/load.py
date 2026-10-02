"""Write extracted rows into DuckDB raw_* schemas. Full refresh per table: sources are small."""
import duckdb


def replace(con: duckdb.DuckDBPyConnection, schema: str, table: str, columns: dict[str, str], rows: list[dict]):
    con.execute(f"create schema if not exists {schema}")
    cols = ", ".join(f'"{c}" {t}' for c, t in columns.items())
    con.execute(f"create or replace table {schema}.{table} ({cols}, _loaded_at timestamp default current_timestamp)")
    if rows:
        names = ", ".join(f'"{c}"' for c in columns)
        con.executemany(
            f"insert into {schema}.{table} ({names}) values ({', '.join('?' * len(columns))})",
            [[r.get(c) for c in columns] for r in rows],
        )
    print(f"  {schema}.{table}: {len(rows)} rows")
