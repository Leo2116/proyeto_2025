# servicios/servicio_pedidos/aplicacion/casos_uso/procesar_orden.py

import uuid
from typing import List
from servicios.servicio_pedidos.dominio.orden import Orden, OrdenItem

# Importamos los Adaptadores de Infraestructura (Servicios)
from servicios.servicio_pedidos.infraestructura.pagos.stripe_cliente import StripeCliente
from servicios.servicio_pedidos.infraestructura.logistica.guatemala_logistica_mock import GuatemalaLogisticaMock

# NOTA: En una implementacion completa se inyectaria un IRepositorioOrden.
# Para este prototipo, simulamos el almacenamiento y el ID de orden aqui.

class ProcesarOrden:
    """
    Logica para tomar un carrito, calcular costos, procesar el pago 
    y crear la orden final.
    """
    def __init__(self, cliente_pagos: StripeCliente, logistica_mock: GuatemalaLogisticaMock):
        # Inyeccion de servicios
        self.cliente_pagos = cliente_pagos
        self.logistica_mock = logistica_mock

    def ejecutar(self, id_usuario: str, items_data: List[dict], direccion_envio: str, token_tarjeta: str) -> dict:
        """
        Ejecuta el flujo completo de checkout.
        """
        
        # 1. Construir Items de Dominio a partir de los datos de entrada
        items = [OrdenItem(
            id_producto=i['id_producto'],
            nombre=i['nombre'],
            precio=i['precio'],
            cantidad=i['cantidad']
        ) for i in items_data]
        
        # 2. Calcular subtotal de productos
        subtotal_productos = sum(item.calcular_subtotal() for item in items)
        
        # 3. Calcular costo de envio (usando el Mock de Guatemala)
        costo_logistica = self.logistica_mock.calcular_costo_envio(direccion_envio)
        
        if not costo_logistica:
            return {'exito': False, 'mensaje': 'No se pudo calcular la tarifa de envio para la direccion proporcionada.'}
        
        costo_envio = costo_logistica['costo']
        
        # 4. Calcular el total final
        total_final = subtotal_productos + costo_envio
        
        # 5. Procesar Pago (llamada al Adaptador de Stripe)
        pago_exitoso = self.cliente_pagos.procesar_pago(
            monto=total_final, 
            token_tarjeta=token_tarjeta,
            descripcion=f"Orden Libreria GT #{id_usuario}"
        )

        if not pago_exitoso:
            return {'exito': False, 'mensaje': 'El pago fue rechazado por la pasarela de pagos. Por favor, intente con otra tarjeta.'}

        # 6. Crear la entidad de Dominio Orden (ID generado)
        id_orden = str(uuid.uuid4())
        orden = Orden(
            id_orden=id_orden,
            id_usuario=id_usuario,
            items=items,
            costo_envio=costo_envio,
            total_final=total_final,
            direccion_envio=direccion_envio,
            estado="PROCESADA" # Cambiar estado tras pago exitoso
        )
        
        # NOTA: Aqui se llamaria al Repositorio de Ordenes para guardar la entidad.
        # Por ahora, simulamos el exito.

        return {
            'exito': True, 
            'mensaje': f'Orden {id_orden} procesada y pagada exitosamente. Total: GTQ {orden.total_final:.2f}',
            'orden': orden.to_dict()
        }