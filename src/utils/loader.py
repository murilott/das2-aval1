import logging
import pyodbc


def load_to_dest(dest_conn_str: str, schema: str, table: str, columns: list, rows: list) -> None:
    """Truncate the destination table and reload with extracted rows."""
    full_table = f"[{schema}].[{table}]"
    col_defs = ", ".join(f"[{c}] NVARCHAR(MAX)" for c in columns)
    col_names = ", ".join(f"[{c}]" for c in columns)
    placeholders = ", ".join("?" for _ in columns)

    # Convert all values to str so pyodbc handles mixed types safely
    def to_str(v):
        return str(v) if v is not None else None

    data = [tuple(to_str(v) for v in row) for row in rows]

    with pyodbc.connect(dest_conn_str) as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{schema}') "
            f"EXEC('CREATE SCHEMA [{schema}]')"
        )

        cursor.execute(
            f"IF NOT EXISTS ("
            f"  SELECT 1 FROM INFORMATION_SCHEMA.TABLES "
            f"  WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'"
            f") CREATE TABLE {full_table} ({col_defs})"
        )

        cursor.execute(f"TRUNCATE TABLE {full_table}")

        cursor.executemany(
            f"INSERT INTO {full_table} ({col_names}) VALUES ({placeholders})",
            data,
        )

        conn.commit()

    logging.info(f"[loader] {len(rows)} linhas carregadas em {full_table}")
