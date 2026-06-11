import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.regiao ON;

MERGE dbo.regiao AS dest
USING #src AS src ON dest.id_regiao = TRY_CAST(src.id_regiao AS int)
WHEN MATCHED THEN UPDATE SET
    cd_regiao         = src.cd_regiao,
    nm_regiao         = src.nm_regiao,
    sg_uf             = src.sg_uf,
    nm_cidade         = src.nm_cidade,
    fl_ativo          = TRY_CAST(src.fl_ativo AS bit),
    dt_atualizacao    = SYSUTCDATETIME(),
    nm_sistema_origem = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_regiao, cd_regiao, nm_regiao, sg_uf, nm_cidade, fl_ativo, nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_regiao AS int), src.cd_regiao, src.nm_regiao, src.sg_uf, src.nm_cidade,
     TRY_CAST(src.fl_ativo AS bit), 'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.regiao OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_regiao(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.regiao")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.regiao")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.regiao: {str(e)}")
        raise
