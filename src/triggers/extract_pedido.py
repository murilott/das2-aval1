import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

# Colunas esperadas na origem:
#   nr_pedido, cd_cliente, cd_representante, cd_regiao,
#   dt_emissao, dt_faturamento, ds_status_pedido,
#   vl_bruto, vl_desconto, vl_liquido, ds_observacao
MERGE_SQL = """
MERGE dbo.pedido AS dest
USING #src AS src ON dest.nr_pedido = src.nr_pedido
WHEN MATCHED THEN UPDATE SET
    id_cliente        = (SELECT id_cliente FROM dbo.cliente
                         WHERE cd_cliente = src.cd_cliente),
    id_representante  = (SELECT id_representante FROM dbo.representante
                         WHERE cd_representante = src.cd_representante),
    id_regiao         = (SELECT id_regiao FROM dbo.regiao
                         WHERE cd_regiao = src.cd_regiao),
    dt_emissao        = TRY_CAST(src.dt_emissao AS datetime2(0)),
    dt_faturamento    = TRY_CAST(src.dt_faturamento AS datetime2(0)),
    ds_status_pedido  = src.ds_status_pedido,
    vl_bruto          = TRY_CAST(src.vl_bruto AS decimal(18,2)),
    vl_desconto       = TRY_CAST(src.vl_desconto AS decimal(18,2)),
    vl_liquido        = TRY_CAST(src.vl_liquido AS decimal(18,2)),
    ds_observacao     = src.ds_observacao,
    dt_atualizacao    = SYSUTCDATETIME(),
    nm_sistema_origem = 'VendaMais_ERP'
WHEN NOT MATCHED THEN INSERT
    (nr_pedido, id_cliente, id_representante, id_regiao,
     dt_emissao, dt_faturamento, ds_status_pedido,
     vl_bruto, vl_desconto, vl_liquido, ds_observacao,
     nm_sistema_origem, cd_registro_origem)
VALUES
    (src.nr_pedido,
     (SELECT id_cliente FROM dbo.cliente WHERE cd_cliente = src.cd_cliente),
     (SELECT id_representante FROM dbo.representante
      WHERE cd_representante = src.cd_representante),
     (SELECT id_regiao FROM dbo.regiao WHERE cd_regiao = src.cd_regiao),
     TRY_CAST(src.dt_emissao AS datetime2(0)),
     TRY_CAST(src.dt_faturamento AS datetime2(0)),
     src.ds_status_pedido,
     TRY_CAST(src.vl_bruto AS decimal(18,2)),
     TRY_CAST(src.vl_desconto AS decimal(18,2)),
     TRY_CAST(src.vl_liquido AS decimal(18,2)),
     src.ds_observacao,
     'VendaMais_ERP', src.nr_pedido);
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
