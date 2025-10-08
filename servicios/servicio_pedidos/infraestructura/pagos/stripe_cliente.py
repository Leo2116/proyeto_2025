# servicios/servicio_pedidos/infraestructura/pagos/stripe_cliente.py

# NOTA: En un proyecto real, se usaria 'import stripe' y se inicializaria con
# stripe.api_key = Config.STRIPE_SECRET_KEY. Aqui lo simularemos.

class StripeCliente:
    """
    Adaptador Mock para la API de Stripe. 
    Simula la creacion de un cargo de pago exitoso o fallido.
    """
    
    def __init__(self):
        # En un entorno real, aqui inicializariamos la SDK de Stripe con la clave secreta.
        pass 

    def procesar_pago(self, monto: float, token_tarjeta: str, descripcion: str) -> bool:
        """
        Simula el procesamiento de un pago en el entorno Sandbox.
        
        Args:
            monto (float): Monto a cobrar en GTQ.
            token_tarjeta (str): Token de tarjeta de prueba (Ej: 'tok_visa').
            descripcion (str): Descripcion del cargo.

        Returns:
            bool: True si el pago es 'aprobado', False si es 'rechazado'.
        """
        
        print(f"Simulando pago de GTQ {monto:.2f} con token: {token_tarjeta}")
        
        # Logica de Sandbox/Prueba:
        # Stripe tiene tokens especiales para simular fallos.
        # Si el token es 'tok_chargeDeclined', simulamos un rechazo.
        if token_tarjeta == 'tok_chargeDeclined':
             print("Pago RECHAZADO (Token de prueba).")
             return False
        
        # En Sandbox, cualquier otro token (como 'tok_visa', 'tok_mastercard') es exitoso.
        print("Pago APROBADO (Sandbox).")
        return True