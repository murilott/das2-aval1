import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

# Colunas esperadas na origem:
#   nr_titulo, cd_cliente, nr_pedido,
#   dt_emissao, dt_vencimento, dt_pagamento,
#   vl_titulo, vl_recebido, ds_status_titulo
MERGE_SQL = """
MERGE dbo.titulo_receber AS dest
USING #src AS src ON dest.nr_titulo = src.nr_titulo
WHEN MATCHED THEN UPDATE SET
    id_cliente        = (SELECT id_cliente FROM dbo.cliente
                         WHERE cd_cliente = src.cd_cliente),
    id_pedido         = (SELECT id_pedido FROM dbo.pedido
                         WHERE nr_pedido = src.nr_pedido),
    dt_emissao        = TRY_CAST(src.dt_emissao AS datetime2(0)),
    dt_vencimento     = TRY_CAST(src.dt_vencimento AS datetime2(0)),
    dt_pagamento      = TRY_CAST(src.dt_pagamento AS datetime2(0)),
    vl_titulo         = TRY_CAST(src.vl_titulo AS decimal(18,2)),
    vl_recebido       = TRY_CAST(src.vl_recebido AS decimal(18,2)),
    ds_status_titulo  = src.ds_status_titulo,
    dt_atualizacao    = SYSUTCDATETIME(),
    nm_sistema_origem = 'VendaMais_ERP'
WHEN NOT MATCHED THEN INSERT
    (nr_titulo, id_cliente, id_pedido,
     dt_emissao, dt_vencimento, dt_pagamento,
     vl_titulo, vl_recebido, ds_status_titulo,
     nm_sistema_origem, cd_registro_origem)
VALUES
    (src.nr_titulo,
     (SELECT id_cliente FROM dbo.cliente WHERE cd_cliente = src.cd_cliente),
     (SELECT id_pedido FROM dbo.pedido WHERE nr_pedido = src.nr_pedido),
     TRY_CAST(src.dt_emissao AS datetime2(0)),
     TRY_CAST(src.dt_vencimento AS datetime2(0)),
     TRY_CAST(src.dt_pagamento AS datetime2(0)),
     TRY_CAST(src.vl_titulo AS decimal(18,2)),
     TRY_CAST(src.vl_recebido AS decimal(18,2)),
     src.ds_status_titulo,
     'VendaMais_ERP', src.nr_titulo);
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_titulo_receber(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.titulo_receber")

    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.titulo_receber")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")

        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)

    except Exception as e:
        logging.error(f"Erro ao processar erp.titulo_receber: {str(e)}")
        raise
