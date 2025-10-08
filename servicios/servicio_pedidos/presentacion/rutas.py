from flask import Blueprint, request, jsonify
import uuid
import datetime
import os
import json

# Importar las capas internas (Aplicación e Infraestructura)
from configuracion import DB_PATH
from servicios.servicio_pedidos.aplicacion.casos_uso.procesar_orden import ProcesarOrden
from servicios.servicio_pedidos.infraestructura.pagos.stripe_cliente import StripeCliente
from servicios.servicio_pedidos.infraestructura.logistica.guatemala_logistica_mock import GuatemalaLogisticaMock
from servicios.servicio_pedidos.infraestructura.persistencia.sqlite_repositorio_orden import SQLiteRepositorioOrden

# Crear el Blueprint de Pedidos
pedidos_bp = Blueprint('pedidos_bp', __name__)

# Adaptadores (Infraestructura)
# Nota: En una aplicación real, estos adaptadores serían inyectados.
REPOSITORIO_ORDEN = SQLiteRepositorioOrden(DB_PATH)
CLIENTE_PAGOS = StripeCliente()
CLIENTE_LOGISTICA = GuatemalaLogisticaMock(DB_PATH)


@pedidos_bp.route('/checkout', methods=['POST'])
def procesar_orden():
    """
    Ruta API para iniciar y procesar una nueva orden de compra.
    """
    data = request.get_json()

    if not data or 'items' not in data or 'usuario_id' not in data:
        return jsonify({"mensaje": "Datos de orden incompletos."}), 400

    # 1. Preparar la inyección de dependencias para el Caso de Uso
    caso_uso = ProcesarOrden(
        repositorio_orden=REPOSITORIO_ORDEN,
        cliente_pagos=CLIENTE_PAGOS,
        cliente_logistica=CLIENTE_LOGISTICA
    )
    
    try:
        # 2. Ejecutar el Caso de Uso (la lógica de negocio)
        orden_id, costo_envio, total = caso_uso.ejecutar(
            usuario_id=data['usuario_id'],
            items_carrito=data['items']
        )
        
        return jsonify({
            "mensaje": "Orden procesada y pagada con éxito.",
            "orden_id": orden_id,
            "costo_envio": costo_envio,
            "total_pagado": total
        }), 201

    except Exception as e:
        # Aquí manejamos errores específicos del negocio (ej: stock insuficiente, pago fallido)
        return jsonify({"mensaje": f"Error al procesar la orden: {str(e)}"}), 500
