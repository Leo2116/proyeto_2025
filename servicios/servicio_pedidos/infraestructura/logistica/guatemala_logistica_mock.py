# servicios/servicio_pedidos/infraestructura/logistica/guatemala_logistica_mock.py

# ¡CORREGIDO! Agregamos 'List' a las importaciones de 'typing'
from typing import Dict, Optional, List
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# Importamos los modelos ORM de la tabla de Logistica
from inicializar_db import LogisticaORM
from configuracion import Config

# Configuracion del motor de SQLAlchemy
Engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=Engine)

# ==============================================================================
# SERVICIO MOCK DE LOGISTICA
# Usa la BD SQLite (inicializada previamente) para simular tarifas de GT.
# ==============================================================================
class GuatemalaLogisticaMock:
    """
    Servicio de Infraestructura que simula el calculo de tarifas de envio 
    para zonas especificas de Guatemala usando la tabla LogisticaORM.
    """
    
    def obtener_tarifas(self) -> List[Dict]:
        """Obtiene todas las tarifas de las zonas de cobertura."""
        session = Session()
        try:
            tarifas = session.query(LogisticaORM).all()
            return [{
                'zona': t.zona_nombre, 
                'tarifa': t.tarifa_gtq, 
                'dias': t.tiempo_estimado_dias
            } for t in tarifas]
        except SQLAlchemyError as e:
            print(f"Error al obtener tarifas de logistica: {e}")
            return []
        finally:
            session.close()

    def calcular_costo_envio(self, direccion_usuario: str) -> Optional[Dict]:
        """
        Busca una tarifa que coincida con la direccion del usuario.
        Esta simulacion es simple y solo verifica si el texto coincide con una zona.
        """
        
        # Simplificacion: buscar la tarifa por zona.
        # En la practica, esto usaria un API de mapeo con geolocalizacion.
        zona_match = None
        
        # Usamos el Mock de tarifas para la simulacion
        tarifas_disponibles = self.obtener_tarifas()
        
        # Intenta hacer un match simple con la direccion
        for tarifa in tarifas_disponibles:
            if tarifa['zona'].lower() in direccion_usuario.lower():
                zona_match = tarifa
                break
        
        if zona_match:
            return {
                'costo': zona_match['tarifa'],
                'dias': zona_match['dias'],
                'zona': zona_match['zona']
            }
        
        # Si no encuentra coincidencia, usa la tarifa de "Resto del Pais"
        # Esto asume que la zona "Resto del Pais" siempre existe en la BD.
        resto_pais = next((t for t in tarifas_disponibles if 'resto' in t['zona'].lower()), None)

        if resto_pais:
            return {
                'costo': resto_pais['tarifa'],
                'dias': resto_pais['dias'],
                'zona': resto_pais['zona']
            }
        
        return None # Falla si ni siquiera encuentra la tarifa por defecto