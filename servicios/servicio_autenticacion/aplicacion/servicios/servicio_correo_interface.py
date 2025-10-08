from abc import ABC, abstractmethod

class IServicioCorreo(ABC):
    """
    Define el contrato para cualquier servicio de envío de correo electrónico.
    Desacopla el Caso de Uso de la implementación concreta (Gmail SMTP, SendGrid, etc.).
    """

    @abstractmethod
    def enviar_correo(self, destinatario: str, asunto: str, cuerpo_html: str) -> None:
        """
        Envía un correo electrónico al destinatario especificado.

        Args:
            destinatario (str): Dirección e-mail del receptor.
            asunto (str): Asunto del correo.
            cuerpo_html (str): Contenido en formato HTML.
        """
        raise NotImplementedError
