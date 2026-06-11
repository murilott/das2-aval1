import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.estoque_saldo ON;

MERGE dbo.estoque_saldo AS dest
USING #src AS src ON dest.id_estoque_saldo = TRY_CAST(src.id_estoque_saldo AS bigint)
WHEN MATCHED THEN UPDATE SET
    id_produto         = TRY_CAST(src.id_produto AS int),
    dt_referencia      = TRY_CAST(src.dt_referencia AS datetime2(0)),
    qt_saldo           = TRY_CAST(src.qt_saldo AS decimal(18,4)),
    dt_atualizacao     = SYSUTCDATETIME(),
    nm_sistema_origem  = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_estoque_saldo, id_produto, dt_referencia, qt_saldo,
     nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_estoque_saldo AS bigint),
     TRY_CAST(src.id_produto AS int),
     TRY_CAST(src.dt_referencia AS datetime2(0)),
     TRY_CAST(src.qt_saldo AS decimal(18,4)),
     'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.estoque_saldo OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_estoque_saldo(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.estoque_saldo")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.estoque_saldo")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.estoque_saldo: {str(e)}")
        raise
