import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.estoque_movimentacao ON;

MERGE dbo.estoque_movimentacao AS dest
USING #src AS src ON dest.id_estoque_movimentacao = TRY_CAST(src.id_estoque_movimentacao AS bigint)
WHEN MATCHED THEN UPDATE SET
    id_produto             = TRY_CAST(src.id_produto AS int),
    dt_movimentacao        = TRY_CAST(src.dt_movimentacao AS datetime2(0)),
    ds_tipo_movimentacao   = src.ds_tipo_movimentacao,
    qt_movimentacao        = TRY_CAST(src.qt_movimentacao AS decimal(18,4)),
    nr_documento_origem    = src.nr_documento_origem,
    id_pedido              = TRY_CAST(src.id_pedido AS bigint),
    ds_observacao          = src.ds_observacao,
    dt_atualizacao         = SYSUTCDATETIME(),
    nm_sistema_origem      = 'VendaMais_ERP',
    cd_registro_origem     = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_estoque_movimentacao, id_produto, dt_movimentacao, ds_tipo_movimentacao,
     qt_movimentacao, nr_documento_origem, id_pedido, ds_observacao,
     nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_estoque_movimentacao AS bigint),
     TRY_CAST(src.id_produto AS int),
     TRY_CAST(src.dt_movimentacao AS datetime2(0)),
     src.ds_tipo_movimentacao,
     TRY_CAST(src.qt_movimentacao AS decimal(18,4)),
     src.nr_documento_origem,
     TRY_CAST(src.id_pedido AS bigint),
     src.ds_observacao,
     'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.estoque_movimentacao OFF;
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
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.estoque_movimentacao: {str(e)}")
        raise
