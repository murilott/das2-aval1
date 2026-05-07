import logging
import azure.functions as func

app = func.FunctionApp()

from triggers.extract_cliente import app as extract_cliente
from triggers.extract_pedido import app as extract_pedido
from triggers.extract_produto import app as extract_produto