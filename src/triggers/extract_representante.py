import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

# Colunas esperadas na origem:
#   cd_representante, nm_representante, ds_email, ds_telefone, cd_regiao, fl_ativo
MERGE_SQL = """
MERGE dbo.representante AS dest
USING #src AS src ON dest.cd_representante = src.cd_representante
WHEN MATCHED THEN UPDATE SET
    nm_representante  = src.nm_representante,
    ds_email          = src.ds_email,
    ds_telefone       = src.ds_telefone,
    id_regiao         = (SELECT id_regiao FROM dbo.regiao WHERE cd_regiao = src.cd_regiao),
    fl_ativo          = CAST(src.fl_ativo AS bit),
    dt_atualizacao    = SYSUTCDATETIME(),
    nm_sistema_origem = 'VendaMais_ERP'
WHEN NOT MATCHED THEN INSERT
    (cd_representante, nm_representante, ds_email, ds_telefone,
     id_regiao, fl_ativo, nm_sistema_origem, cd_registro_origem)
VALUES
    (src.cd_representante, src.nm_representante, src.ds_email, src.ds_telefone,
     (SELECT id_regiao FROM dbo.regiao WHERE cd_regiao = src.cd_regiao),
     CAST(src.fl_ativo AS bit), 'VendaMais_ERP', src.cd_representante);
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
