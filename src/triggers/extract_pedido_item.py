import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.pedido_item ON;

MERGE dbo.pedido_item AS dest
USING #src AS src ON dest.id_pedido_item = TRY_CAST(src.id_pedido_item AS bigint)
WHEN MATCHED THEN UPDATE SET
    id_pedido          = TRY_CAST(src.id_pedido AS bigint),
    id_produto         = TRY_CAST(src.id_produto AS int),
    nr_sequencia_item  = TRY_CAST(src.nr_sequencia_item AS int),
    qt_item            = TRY_CAST(src.qt_item AS decimal(18,4)),
    vl_preco_unitario  = TRY_CAST(src.vl_preco_unitario AS decimal(18,4)),
    vl_bruto           = TRY_CAST(src.vl_bruto AS decimal(18,2)),
    vl_desconto        = TRY_CAST(src.vl_desconto AS decimal(18,2)),
    vl_liquido         = TRY_CAST(src.vl_liquido AS decimal(18,2)),
    dt_atualizacao     = SYSUTCDATETIME(),
    nm_sistema_origem  = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_pedido_item, id_pedido, id_produto, nr_sequencia_item,
     qt_item, vl_preco_unitario, vl_bruto, vl_desconto, vl_liquido,
     nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_pedido_item AS bigint),
     TRY_CAST(src.id_pedido AS bigint), TRY_CAST(src.id_produto AS int),
     TRY_CAST(src.nr_sequencia_item AS int),
     TRY_CAST(src.qt_item AS decimal(18,4)),
     TRY_CAST(src.vl_preco_unitario AS decimal(18,4)),
     TRY_CAST(src.vl_bruto AS decimal(18,2)),
     TRY_CAST(src.vl_desconto AS decimal(18,2)),
     TRY_CAST(src.vl_liquido AS decimal(18,2)),
     'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.pedido_item OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_pedido_item(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.pedido_item")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.pedido_item")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.pedido_item: {str(e)}")
        raise
