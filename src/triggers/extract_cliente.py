import azure.functions as func
import logging
import pyodbc

from utils.db_helper import get_source_conn_str, get_dest_conn_str
from utils.merger import merge_to_dbo

app = func.Blueprint()

# Colunas esperadas na origem:
#   cd_cliente, nm_cliente, tp_pessoa, nr_cnpj_cpf, ds_email, ds_telefone,
#   cd_regiao, cd_representante, dt_cadastro, fl_ativo
MERGE_SQL = """
MERGE dbo.cliente AS dest
USING #src AS src ON dest.cd_cliente = src.cd_cliente
WHEN MATCHED THEN UPDATE SET
    nm_cliente        = src.nm_cliente,
    tp_pessoa         = src.tp_pessoa,
    nr_cnpj_cpf       = src.nr_cnpj_cpf,
    ds_email          = src.ds_email,
    ds_telefone       = src.ds_telefone,
    id_regiao         = (SELECT id_regiao FROM dbo.regiao
                         WHERE cd_regiao = src.cd_regiao),
    id_representante  = (SELECT id_representante FROM dbo.representante
                         WHERE cd_representante = src.cd_representante),
    dt_cadastro       = TRY_CAST(src.dt_cadastro AS datetime2(0)),
    fl_ativo          = CAST(src.fl_ativo AS bit),
    dt_atualizacao    = SYSUTCDATETIME(),
    nm_sistema_origem = 'VendaMais_ERP'
WHEN NOT MATCHED THEN INSERT
    (cd_cliente, nm_cliente, tp_pessoa, nr_cnpj_cpf, ds_email, ds_telefone,
     id_regiao, id_representante, dt_cadastro, fl_ativo,
     nm_sistema_origem, cd_registro_origem)
VALUES
    (src.cd_cliente, src.nm_cliente, src.tp_pessoa, src.nr_cnpj_cpf,
     src.ds_email, src.ds_telefone,
     (SELECT id_regiao FROM dbo.regiao WHERE cd_regiao = src.cd_regiao),
     (SELECT id_representante FROM dbo.representante
      WHERE cd_representante = src.cd_representante),
     TRY_CAST(src.dt_cadastro AS datetime2(0)),
     CAST(src.fl_ativo AS bit), 'VendaMais_ERP', src.cd_cliente);
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
