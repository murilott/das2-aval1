import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import delete_insert_dbo

app = func.Blueprint()

# Colunas esperadas na origem: cd_sku, dt_referencia, qt_saldo
INSERT_SQL = """
INSERT INTO dbo.estoque_saldo (id_produto, dt_referencia, qt_saldo, nm_sistema_origem)
SELECT
    (SELECT id_produto FROM dbo.produto WHERE cd_sku = src.cd_sku),
    TRY_CAST(src.dt_referencia AS datetime2(0)),
    TRY_CAST(src.qt_saldo AS decimal(18,4)),
    'VendaMais_ERP'
FROM #src AS src
WHERE (SELECT id_produto FROM dbo.produto WHERE cd_sku = src.cd_sku) IS NOT NULL;
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

        delete_insert_dbo(get_dest_conn_str(), columns, rows,
                          "dbo.estoque_saldo", INSERT_SQL)

    except Exception as e:
        logging.error(f"Erro ao processar erp.estoque_saldo: {str(e)}")
        raise
