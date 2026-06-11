import logging
import pyodbc


def merge_to_dbo(dest_conn_str: str, columns: list, rows: list, merge_sql: str) -> None:
    """
    Cria uma tabela temporária #src com as colunas da origem (todas NVARCHAR),
    faz bulk insert e executa o MERGE informado contra dbo.
    """
    col_defs = ", ".join(f"[{c}] NVARCHAR(MAX)" for c in columns)
    col_names = ", ".join(f"[{c}]" for c in columns)
    placeholders = ", ".join("?" for _ in columns)

    def to_str(v):
        return str(v) if v is not None else None

    data = [tuple(to_str(v) for v in row) for row in rows]

    with pyodbc.connect(dest_conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(f"CREATE TABLE #src ({col_defs})")
        cursor.executemany(f"INSERT INTO #src ({col_names}) VALUES ({placeholders})", data)
        cursor.execute(merge_sql)
        conn.commit()

    logging.info(f"[merger] MERGE concluído — {len(rows)} linhas processadas")


def delete_insert_dbo(dest_conn_str: str, columns: list, rows: list, table: str, insert_sql: str) -> None:
    """
    Para tabelas sem chave de negócio única (estoque_saldo, estoque_movimentacao):
    DELETE WHERE nm_sistema_origem = 'VendaMais_ERP' e INSERT tudo novamente.
    """
    col_defs = ", ".join(f"[{c}] NVARCHAR(MAX)" for c in columns)
    col_names = ", ".join(f"[{c}]" for c in columns)
    placeholders = ", ".join("?" for _ in columns)

    def to_str(v):
        return str(v) if v is not None else None

    data = [tuple(to_str(v) for v in row) for row in rows]

    with pyodbc.connect(dest_conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table} WHERE nm_sistema_origem = 'VendaMais_ERP'")
        cursor.execute(f"CREATE TABLE #src ({col_defs})")
        cursor.executemany(f"INSERT INTO #src ({col_names}) VALUES ({placeholders})", data)
        cursor.execute(insert_sql)
        conn.commit()

    logging.info(f"[merger] DELETE+INSERT concluído em {table} — {len(rows)} linhas")
