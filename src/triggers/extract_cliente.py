import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

MERGE_SQL = """
SET IDENTITY_INSERT dbo.cliente ON;

MERGE dbo.cliente AS dest
USING #src AS src ON dest.id_cliente = TRY_CAST(src.id_cliente AS int)
WHEN MATCHED THEN UPDATE SET
    cd_cliente         = src.cd_cliente,
    nm_cliente         = src.nm_cliente,
    tp_pessoa          = src.tp_pessoa,
    nr_cnpj_cpf        = src.nr_cnpj_cpf,
    ds_email           = src.ds_email,
    ds_telefone        = src.ds_telefone,
    id_regiao          = TRY_CAST(src.id_regiao AS int),
    id_representante   = TRY_CAST(src.id_representante AS int),
    dt_cadastro        = TRY_CAST(src.dt_cadastro AS datetime2(0)),
    fl_ativo           = TRY_CAST(src.fl_ativo AS bit),
    dt_atualizacao     = SYSUTCDATETIME(),
    nm_sistema_origem  = 'VendaMais_ERP',
    cd_registro_origem = src.cd_registro_origem
WHEN NOT MATCHED THEN INSERT
    (id_cliente, cd_cliente, nm_cliente, tp_pessoa, nr_cnpj_cpf, ds_email, ds_telefone,
     id_regiao, id_representante, dt_cadastro, fl_ativo, nm_sistema_origem, cd_registro_origem)
VALUES
    (TRY_CAST(src.id_cliente AS int), src.cd_cliente, src.nm_cliente, src.tp_pessoa,
     src.nr_cnpj_cpf, src.ds_email, src.ds_telefone,
     TRY_CAST(src.id_regiao AS int), TRY_CAST(src.id_representante AS int),
     TRY_CAST(src.dt_cadastro AS datetime2(0)),
     TRY_CAST(src.fl_ativo AS bit), 'VendaMais_ERP', src.cd_registro_origem);

SET IDENTITY_INSERT dbo.cliente OFF;
"""


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_cliente(timer: func.TimerRequest) -> None:
    logging.info("Iniciando extração: erp.cliente")
    try:
        with pyodbc.connect(get_source_conn_str()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM erp.cliente")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        logging.info(f"Extraídos {len(rows)} registros | colunas: {columns}")
        merge_to_dbo(get_dest_conn_str(), columns, rows, MERGE_SQL)
    except Exception as e:
        logging.error(f"Erro ao processar erp.cliente: {str(e)}")
        raise
