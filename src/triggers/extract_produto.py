import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.produto ON;

MERGE dbo.produto AS dest
USING #src AS src ON dest.id_produto = TRY_CAST(src.id_produto AS int)
WHEN MATCHED THEN UPDATE SET
    cd_produto          = src.cd_produto,
    cd_sku              = src.cd_sku,
    nm_produto          = src.nm_produto,
    id_categoria        = TRY_CAST(src.id_categoria AS int),
    nm_unidade_medida   = src.nm_unidade_medida,
    qt_ponto_reposicao  = TRY_CAST(src.qt_ponto_reposicao AS decimal(18,4)),
    fl_ativo            = TRY_CAST(src.fl_ativo AS bit),
    dt_atualizacao      = SYSUTCDATETIME(),
    nm_sistema_origem   = 'VendaMais_ERP',
    cd_registro_origem  = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_produto, cd_produto, cd_sku, nm_produto, id_categoria, nm_unidade_medida,
     qt_ponto_reposicao, fl_ativo, nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_produto AS int), src.cd_produto, src.cd_sku, src.nm_produto,
     TRY_CAST(src.id_categoria AS int), src.nm_unidade_medida,
     TRY_CAST(src.qt_ponto_reposicao AS decimal(18,4)),
     TRY_CAST(src.fl_ativo AS bit), 'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.produto OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_produto(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.produto")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.produto")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.produto: {str(e)}")
        raise
