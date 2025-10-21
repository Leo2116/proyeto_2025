"""
Cliente SMTP básico para envío de correos de verificación.

- Usa variables de entorno (cargadas por python-dotenv si hay .env).
- Soporta STARTTLS (587) y SSL directo (465) vía SMTP_USE_TLS / SMTP_USE_SSL.
- Mensajes en ASCII para compatibilidad en Windows.
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv, find_dotenv

from servicios.servicio_autenticacion.aplicacion.servicios.servicio_correo_interface import IServicioCorreo

# Cargar variables de entorno desde .env en la raíz del proyecto (si existe)
load_dotenv(find_dotenv())


class GoogleSMTPCliente(IServicioCorreo):
    """
    Implementación de IServicioCorreo usando servidor SMTP (por defecto Gmail).
    Requiere contraseña de aplicación si usas Gmail.
    """

    def __init__(self):
        # Permitir variables MAIL_* como fallback
        self.smtp_server = os.getenv("SMTP_SERVER") or os.getenv("MAIL_SERVER") or "smtp.gmail.com"
        self.smtp_port = int(os.getenv("SMTP_PORT") or os.getenv("MAIL_PORT") or "587")
        self.smtp_user = os.getenv("SMTP_USER") or os.getenv("MAIL_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD") or os.getenv("MAIL_PASSWORD")
        self.smtp_from_name = os.getenv("SMTP_FROM_NAME") or os.getenv("MAIL_DEFAULT_SENDER") or "Libreria Jehova Jireh"
        self.smtp_use_tls = (os.getenv("SMTP_USE_TLS") or os.getenv("MAIL_USE_TLS") or "true").lower() == "true"
        self.smtp_use_ssl = (os.getenv("SMTP_USE_SSL") or os.getenv("MAIL_USE_SSL") or "false").lower() == "true"
        self.smtp_timeout = int(os.getenv("SMTP_TIMEOUT") or os.getenv("MAIL_TIMEOUT") or "30")
        self.suppress_send = (os.getenv("MAIL_SUPPRESS_SEND") or "false").lower() == "true"

        if not self.smtp_user or not self.smtp_password:
            print("ADVERTENCIA: SMTP_USER/SMTP_PASSWORD no configurados en .env. No se podran enviar correos.")

    # Alias por compatibilidad
    def enviar_email(self, para: str, asunto: str, html: str, texto_plano: str | None = None) -> None:
        return self.enviar_correo(destinatario=para, asunto=asunto, cuerpo_html=html, texto_plano=texto_plano)

    def enviar_correo(self, destinatario: str, asunto: str, cuerpo_html: str, texto_plano: str | None = None) -> None:
        """
        Envia correo HTML usando TLS (STARTTLS) o SSL según configuración.
        """
        if not self.smtp_user or not self.smtp_password:
            print(f"ERROR SMTP: faltan credenciales. No se enviara a {destinatario}.")
            return

        if self.suppress_send:
            print(f"[SMTP SUPPRESS] To:{destinatario} Subject:{asunto}")
            return

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.smtp_from_name} <{self.smtp_user}>"
        msg["To"] = destinatario
        msg["Subject"] = asunto

        texto_plano = texto_plano or "Para ver este mensaje, habilita contenido HTML."
        part_text = MIMEText(texto_plano, "plain", "utf-8")
        part_html = MIMEText(cuerpo_html, "html", "utf-8")
        msg.attach(part_text)
        msg.attach(part_html)

        if self.smtp_use_ssl:
            try:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=self.smtp_timeout, context=context) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.smtp_user, destinatario, msg.as_string())
                print(f"Correo enviado a: {destinatario}")
                return
            except Exception as e:
                print(f"Error al enviar correo SMTP (SSL) a {destinatario}: {e}")
                raise

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.smtp_timeout) as server:
                server.ehlo()
                if self.smtp_use_tls:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, destinatario, msg.as_string())
            print(f"Correo enviado a: {destinatario}")
        except Exception as e:
            print(f"Error al enviar correo SMTP a {destinatario}: {e}")
            raise
