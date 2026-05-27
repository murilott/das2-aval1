import azure.functions as func
import logging
import os
import pyodbc
import time
from sqlalchemy import create_engine, text, URL  
#from orchestrators.etl_orchestrator import ETLOrchestrator

app = func.Blueprint()

@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False,
            use_monitor=False) 
def poc_teste_cliente(timer: func.TimerRequest) -> None:
    sql_server = os.getenv("SQL_SERVER_SOURCE")
    database = os.getenv("SQL_DATABASE_SOURCE")
    user = os.getenv("SQL_USER_SOURCE")
    password = os.getenv("SQL_PASSWORD_SOURCE")
    
    logging.info(f"Iniciando | Servidor {sql_server}, banco: {database}, usuário: {user}, senha: {password}")
    
    # Configura a string de conexão para o banco de dados SQL Server
    conn_str = URL.create(
        "mssql+pyodbc",
        host=sql_server,
        database=database,
        username=user,
        password=password,
        query={
            "driver": "ODBC Driver 18 for SQL Server",
            "Encrypt": "yes",
            "TrustServerCertificate": "no",
            "Connection Timeout": "30"
        }
    )
    
    engine = create_engine(conn_str)
    
    try:
        
        logging.info("Iniciando medição com SQLAlchemy...")
        
        inicio = time.perf_counter()
        # Estabelece a conexão com o banco de dados usando pyodbc
        with engine.connect() as conn:
            query = text("select top 5 * from erp.cliente")

            # Executa a consulta SQL
            result = conn.execute(query)

            # Busca todos os resultados da consulta
            rows = [dict(row) for row in result.mappings()]
            
            # Exibe no log de forma estruturada
            for row in rows:
                logging.info(f"Cliente extraído: {row}")

        fim = time.perf_counter()
        duracao = (fim - inicio) * 1000
        
        logging.info(f"terminando medição. Tempo de execução: {duracao:.2f} ms")

    except Exception as e:
        logging.error(f"Erro ao ler erp.cliente: {str(e)}")
        raise