import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

# Colunas fonte: id_entrega, id_pedido, id_transportadora, id_regiao,
#                dt_prometida, dt_entrega, ds_status_entrega, cd_rastreio,
#                nm_sistema_origem, cd_registro_origem
MERGE_SQL = """
SET IDENTITY_INSERT dbo.entrega ON;

MERGE dbo.entrega AS dest
USING #src AS src ON dest.id_entrega = TRY_CAST(src.id_entrega AS bigint)
WHEN MATCHED THEN UPDATE SET
    id_pedido          = TRY_CAST(src.id_pedido AS bigint),
    id_transportadora  = TRY_CAST(src.id_transportadora AS int),
    id_regiao          = TRY_CAST(src.id_regiao AS int),
    dt_prometida       = TRY_CAST(src.dt_prometida AS datetime2(0)),
    dt_entrega         = TRY_CAST(src.dt_entrega AS datetime2(0)),
    ds_status_entrega  = src.ds_status_entrega,
    cd_rastreio        = src.cd_rastreio,
    dt_atualizacao     = SYSUTCDATETIME(),
    nm_sistema_origem  = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_entrega, id_pedido, id_transportadora, id_regiao,
     dt_prometida, dt_entrega, ds_status_entrega, cd_rastreio,
     nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_entrega AS bigint),
     TRY_CAST(src.id_pedido AS bigint),
     TRY_CAST(src.id_transportadora AS int),
     TRY_CAST(src.id_regiao AS int),
     TRY_CAST(src.dt_prometida AS datetime2(0)),
     TRY_CAST(src.dt_entrega AS datetime2(0)),
     src.ds_status_entrega, src.cd_rastreio,
     'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.entrega OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_entrega(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.entrega")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.entrega")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.entrega: {str(e)}")
        raise
