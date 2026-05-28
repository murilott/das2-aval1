import azure.functions as func
import logging
import os
import pyodbc
import time
#from orchestrators.etl_orchestrator import ETLOrchestrator

app = func.Blueprint()


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_entrega(timer: func.TimerRequest) -> None:
    sql_server = os.getenv("SQL_SERVER_SOURCE")
    database = os.getenv("SQL_DATABASE_SOURCE")
    user = os.getenv("SQL_USER_SOURCE")
    password = os.getenv("SQL_PASSWORD_SOURCE")
    
    logging.info(f"servidor {sql_server}, banco: {database}, usuário: {user}, senha: {password}")

    # Configura a string de conexão para o banco de dados SQL Server
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={sql_server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    
    try:
        logging.info("Iniciando medição com PyODBC...")
        
        inicio = time.perf_counter()
        # Estabelece a conexão com o banco de dados usando pyodbc
        with pyodbc.connect(conn_str) as conn:
            # Cria um cursor para executar a consulta   
            cursor = conn.cursor()
            
            query = "select * from erp.entrega"

            # Executa a consulta SQL
            cursor.execute(query)

            # Busca todos os resultados da consulta
            rows = cursor.fetchall()

            logging.info(rows)  

            fim = time.perf_counter()
            duracao = (fim - inicio) * 1000
            
            logging.info(f"terminando medição. Tempo de execução: {duracao:.2f} ms")         

    except Exception as e:
        logging.error(f"Erro ao ler erp.cliente: {str(e)}")
        raise