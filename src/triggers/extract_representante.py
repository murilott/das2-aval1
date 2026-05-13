import azure.functions as func
import logging
import os
#from orchestrators.etl_orchestrator import ETLOrchestrator

app = func.Blueprint()


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def extract_representante(timer: func.TimerRequest) -> None:
    sql_server = os.getenv("SQL_SERVER_SOURCE")
    database = os.getenv("SQL_DATABASE_SOURCE")
    user = os.getenv("SQL_USER_SOURCE")
    password = os.getenv("SQL_PASSWORD_SOURCE")
    
    logging.info(f"servidor {sql_server}, banco: {database}, usuário: {user}, senha: {password}")
