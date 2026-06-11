import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.pedido ON;

MERGE dbo.pedido AS dest
USING #src AS src ON dest.id_pedido = TRY_CAST(src.id_pedido AS bigint)
WHEN MATCHED THEN UPDATE SET
    nr_pedido          = src.nr_pedido,
    id_cliente         = TRY_CAST(src.id_cliente AS int),
    id_representante   = TRY_CAST(src.id_representante AS int),
    id_regiao          = TRY_CAST(src.id_regiao AS int),
    dt_emissao         = TRY_CAST(src.dt_emissao AS datetime2(0)),
    dt_faturamento     = TRY_CAST(src.dt_faturamento AS datetime2(0)),
    ds_status_pedido   = src.ds_status_pedido,
    vl_bruto           = TRY_CAST(src.vl_bruto AS decimal(18,2)),
    vl_desconto        = TRY_CAST(src.vl_desconto AS decimal(18,2)),
    vl_liquido         = TRY_CAST(src.vl_liquido AS decimal(18,2)),
    ds_observacao      = src.ds_observacao,
    dt_atualizacao     = SYSUTCDATETIME(),
    nm_sistema_origem  = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_pedido, nr_pedido, id_cliente, id_representante, id_regiao,
     dt_emissao, dt_faturamento, ds_status_pedido,
     vl_bruto, vl_desconto, vl_liquido, ds_observacao,
     nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_pedido AS bigint), src.nr_pedido,
     TRY_CAST(src.id_cliente AS int), TRY_CAST(src.id_representante AS int),
     TRY_CAST(src.id_regiao AS int),
     TRY_CAST(src.dt_emissao AS datetime2(0)),
     TRY_CAST(src.dt_faturamento AS datetime2(0)),
     src.ds_status_pedido,
     TRY_CAST(src.vl_bruto AS decimal(18,2)),
     TRY_CAST(src.vl_desconto AS decimal(18,2)),
     TRY_CAST(src.vl_liquido AS decimal(18,2)),
     src.ds_observacao, 'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.pedido OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_pedido(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.pedido")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.pedido")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.pedido: {str(e)}")
        raise
