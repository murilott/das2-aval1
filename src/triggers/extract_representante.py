import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.representante ON;

MERGE dbo.representante AS dest
USING #src AS src ON dest.id_representante = TRY_CAST(src.id_representante AS int)
WHEN MATCHED THEN UPDATE SET
    cd_representante   = src.cd_representante,
    nm_representante   = src.nm_representante,
    ds_email           = src.ds_email,
    ds_telefone        = src.ds_telefone,
    id_regiao          = TRY_CAST(src.id_regiao AS int),
    fl_ativo           = TRY_CAST(src.fl_ativo AS bit),
    dt_atualizacao     = SYSUTCDATETIME(),
    nm_sistema_origem  = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_representante, cd_representante, nm_representante, ds_email, ds_telefone,
     id_regiao, fl_ativo, nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_representante AS int), src.cd_representante, src.nm_representante,
     src.ds_email, src.ds_telefone, TRY_CAST(src.id_regiao AS int),
     TRY_CAST(src.fl_ativo AS bit), 'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.representante OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_representante(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.representante")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.representante")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.representante: {str(e)}")
        raise
