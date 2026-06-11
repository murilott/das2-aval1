import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.titulo_receber ON;

MERGE dbo.titulo_receber AS dest
USING #src AS src ON dest.id_titulo_receber = TRY_CAST(src.id_titulo_receber AS bigint)
WHEN MATCHED THEN UPDATE SET
    nr_titulo          = src.nr_titulo,
    id_cliente         = TRY_CAST(src.id_cliente AS int),
    id_pedido          = TRY_CAST(src.id_pedido AS bigint),
    dt_emissao         = TRY_CAST(src.dt_emissao AS datetime2(0)),
    dt_vencimento      = TRY_CAST(src.dt_vencimento AS datetime2(0)),
    dt_pagamento       = TRY_CAST(src.dt_pagamento AS datetime2(0)),
    vl_titulo          = TRY_CAST(src.vl_titulo AS decimal(18,2)),
    vl_recebido        = TRY_CAST(src.vl_recebido AS decimal(18,2)),
    ds_status_titulo   = src.ds_status_titulo,
    dt_atualizacao     = SYSUTCDATETIME(),
    nm_sistema_origem  = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_titulo_receber, nr_titulo, id_cliente, id_pedido,
     dt_emissao, dt_vencimento, dt_pagamento,
     vl_titulo, vl_recebido, ds_status_titulo,
     nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_titulo_receber AS bigint), src.nr_titulo,
     TRY_CAST(src.id_cliente AS int), TRY_CAST(src.id_pedido AS bigint),
     TRY_CAST(src.dt_emissao AS datetime2(0)),
     TRY_CAST(src.dt_vencimento AS datetime2(0)),
     TRY_CAST(src.dt_pagamento AS datetime2(0)),
     TRY_CAST(src.vl_titulo AS decimal(18,2)),
     TRY_CAST(src.vl_recebido AS decimal(18,2)),
     src.ds_status_titulo, 'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.titulo_receber OFF;
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
