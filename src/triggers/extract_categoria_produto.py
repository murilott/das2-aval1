import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

# Colunas fonte: id_categoria, cd_categoria, nm_categoria, fl_ativo, ...
MERGE_SQL = """
SET IDENTITY_INSERT dbo.categoria_produto ON;

MERGE dbo.categoria_produto AS dest
USING #src AS src ON dest.id_categoria = TRY_CAST(src.id_categoria AS int)
WHEN MATCHED THEN UPDATE SET
    cd_categoria      = src.cd_categoria,
    nm_categoria      = src.nm_categoria,
    fl_ativo          = TRY_CAST(src.fl_ativo AS bit),
    dt_atualizacao    = SYSUTCDATETIME(),
    nm_sistema_origem = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_categoria, cd_categoria, nm_categoria, fl_ativo, nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_categoria AS int), src.cd_categoria, src.nm_categoria,
     TRY_CAST(src.fl_ativo AS bit), 'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.categoria_produto OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_categoria_produto(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.categoria_produto")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.categoria_produto")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.categoria_produto: {str(e)}")
        raise
