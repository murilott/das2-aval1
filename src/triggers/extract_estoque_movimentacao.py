import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import delete_insert_dbo

app = func.Blueprint()

# Colunas esperadas na origem:
#   cd_sku, dt_movimentacao, ds_tipo_movimentacao, qt_movimentacao,
#   nr_documento_origem, nr_pedido, ds_observacao
INSERT_SQL = """
INSERT INTO dbo.estoque_movimentacao
    (id_produto, dt_movimentacao, ds_tipo_movimentacao, qt_movimentacao,
     nr_documento_origem, id_pedido, ds_observacao, nm_sistema_origem)
SELECT
    (SELECT id_produto FROM dbo.produto WHERE cd_sku = src.cd_sku),
    TRY_CAST(src.dt_movimentacao AS datetime2(0)),
    src.ds_tipo_movimentacao,
    TRY_CAST(src.qt_movimentacao AS decimal(18,4)),
    src.nr_documento_origem,
    (SELECT id_pedido FROM dbo.pedido WHERE nr_pedido = src.nr_pedido),
    src.ds_observacao,
    'VendaMais_ERP'
FROM #src AS src
WHERE (SELECT id_produto FROM dbo.produto WHERE cd_sku = src.cd_sku) IS NOT NULL;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_estoque_movimentacao(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.estoque_movimentacao")

    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.estoque_movimentacao")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")

        delete_insert_dbo(get_dest_conn_str(), columns, rows,
                          "dbo.estoque_movimentacao", INSERT_SQL)

    except Exception as e:
        logging.error(f"Erro ao processar erp.estoque_movimentacao: {str(e)}")
        raise
