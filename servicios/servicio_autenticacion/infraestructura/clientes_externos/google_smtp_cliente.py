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
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_from_name = os.getenv("SMTP_FROM_NAME", "Libreria Jehova Jireh")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.smtp_use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
        self.smtp_timeout = int(os.getenv("SMTP_TIMEOUT", "30"))

        if not self.smtp_user or not self.smtp_password:
            print("ADVERTENCIA: SMTP_USER/SMTP_PASSWORD no configurados en .env. No se podran enviar correos.")

    def enviar_correo(self, destinatario: str, asunto: str, cuerpo_html: str) -> None:
        """
        Envia correo HTML usando TLS (STARTTLS) o SSL según configuración.
        """
        if not self.smtp_user or not self.smtp_password:
            print(f"ERROR SMTP: faltan credenciales. No se enviara a {destinatario}.")
            return

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.smtp_from_name} <{self.smtp_user}>"
        msg["To"] = destinatario
        msg["Subject"] = asunto

        texto_plano = "Para ver este mensaje, habilita contenido HTML."
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

