import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

# Colunas esperadas na origem:
#   nr_pedido, cd_transportadora, cd_regiao,
#   dt_prometida, dt_entrega, ds_status_entrega, cd_rastreio, ds_observacao
MERGE_SQL = """
MERGE dbo.entrega AS dest
USING #src AS src
ON dest.id_pedido = (SELECT id_pedido FROM dbo.pedido WHERE nr_pedido = src.nr_pedido)
WHEN MATCHED THEN UPDATE SET
    id_transportadora  = (SELECT id_transportadora FROM dbo.transportadora
                          WHERE cd_transportadora = src.cd_transportadora),
    id_regiao          = (SELECT id_regiao FROM dbo.regiao
                          WHERE cd_regiao = src.cd_regiao),
    dt_prometida       = TRY_CAST(src.dt_prometida AS datetime2(0)),
    dt_entrega         = TRY_CAST(src.dt_entrega AS datetime2(0)),
    ds_status_entrega  = src.ds_status_entrega,
    cd_rastreio        = src.cd_rastreio,
    ds_observacao      = src.ds_observacao,
    dt_atualizacao     = SYSUTCDATETIME(),
    nm_sistema_origem  = 'VendaMais_ERP'
WHEN NOT MATCHED THEN INSERT
    (id_pedido, id_transportadora, id_regiao,
     dt_prometida, dt_entrega, ds_status_entrega,
     cd_rastreio, ds_observacao, nm_sistema_origem)
VALUES
    ((SELECT id_pedido FROM dbo.pedido WHERE nr_pedido = src.nr_pedido),
     (SELECT id_transportadora FROM dbo.transportadora
      WHERE cd_transportadora = src.cd_transportadora),
     (SELECT id_regiao FROM dbo.regiao WHERE cd_regiao = src.cd_regiao),
     TRY_CAST(src.dt_prometida AS datetime2(0)),
     TRY_CAST(src.dt_entrega AS datetime2(0)),
     src.ds_status_entrega,
     src.cd_rastreio,
     src.ds_observacao,
     'VendaMais_ERP');
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
