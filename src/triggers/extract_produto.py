import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

# Colunas esperadas na origem:
#   cd_produto, cd_sku, nm_produto, cd_categoria, nm_unidade_medida, qt_ponto_reposicao, fl_ativo
MERGE_SQL = """
MERGE dbo.produto AS dest
USING #src AS src ON dest.cd_sku = src.cd_sku
WHEN MATCHED THEN UPDATE SET
    cd_produto          = src.cd_produto,
    nm_produto          = src.nm_produto,
    id_categoria        = (SELECT id_categoria FROM dbo.categoria_produto
                           WHERE cd_categoria = src.cd_categoria),
    nm_unidade_medida   = src.nm_unidade_medida,
    qt_ponto_reposicao  = TRY_CAST(src.qt_ponto_reposicao AS decimal(18,4)),
    fl_ativo            = CAST(src.fl_ativo AS bit),
    dt_atualizacao      = SYSUTCDATETIME(),
    nm_sistema_origem   = 'VendaMais_ERP'
WHEN NOT MATCHED THEN INSERT
    (cd_produto, cd_sku, nm_produto, id_categoria, nm_unidade_medida,
     qt_ponto_reposicao, fl_ativo, nm_sistema_origem, cd_registro_origem)
VALUES
    (src.cd_produto, src.cd_sku, src.nm_produto,
     (SELECT id_categoria FROM dbo.categoria_produto WHERE cd_categoria = src.cd_categoria),
     src.nm_unidade_medida, TRY_CAST(src.qt_ponto_reposicao AS decimal(18,4)),
     CAST(src.fl_ativo AS bit), 'VendaMais_ERP', src.cd_sku);
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
