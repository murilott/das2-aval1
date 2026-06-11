import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

# Colunas esperadas na origem: cd_regiao, nm_regiao, sg_uf, nm_cidade, fl_ativo
MERGE_SQL = """
MERGE dbo.regiao AS dest
USING #src AS src ON dest.cd_regiao = src.cd_regiao
WHEN MATCHED THEN UPDATE SET
    nm_regiao         = src.nm_regiao,
    sg_uf             = src.sg_uf,
    nm_cidade         = src.nm_cidade,
    fl_ativo          = CAST(src.fl_ativo AS bit),
    dt_atualizacao    = SYSUTCDATETIME(),
    nm_sistema_origem = 'VendaMais_ERP'
WHEN NOT MATCHED THEN INSERT
    (cd_regiao, nm_regiao, sg_uf, nm_cidade, fl_ativo, nm_sistema_origem, cd_registro_origem)
VALUES
    (src.cd_regiao, src.nm_regiao, src.sg_uf, src.nm_cidade,
     CAST(src.fl_ativo AS bit), 'VendaMais_ERP', src.cd_regiao);
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
