import logging
import azure.functions as func

app = func.FunctionApp()

# importação das functions
from triggers.extract_cliente import app as extract_cliente
from triggers.extract_pedido import app as extract_pedido
from triggers.extract_produto import app as extract_produto

# registrar e rodar functions
app.register_functions(extract_cliente)
app.register_functions(extract_pedido)
app.register_functions(extract_produto)