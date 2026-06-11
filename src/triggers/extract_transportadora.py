import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.transportadora ON;

MERGE dbo.transportadora AS dest
USING #src AS src ON dest.id_transportadora = TRY_CAST(src.id_transportadora AS int)
WHEN MATCHED THEN UPDATE SET
    cd_transportadora  = src.cd_transportadora,
    nm_transportadora  = src.nm_transportadora,
    nr_cnpj            = src.nr_cnpj,
    ds_telefone        = src.ds_telefone,
    fl_ativo           = TRY_CAST(src.fl_ativo AS bit),
    dt_atualizacao     = SYSUTCDATETIME(),
    nm_sistema_origem  = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_transportadora, cd_transportadora, nm_transportadora, nr_cnpj, ds_telefone,
     fl_ativo, nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_transportadora AS int), src.cd_transportadora, src.nm_transportadora,
     src.nr_cnpj, src.ds_telefone, TRY_CAST(src.fl_ativo AS bit),
     'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.transportadora OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_transportadora(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.transportadora")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.transportadora")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.transportadora: {str(e)}")
        raise
