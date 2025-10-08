# servicios/servicio_autenticacion/aplicacion/casos_uso/enviar_verificacion_correo.py
"""
Caso de uso: generar token de verificación, guardarlo en el repositorio y enviar el email
Se asume que el repositorio implementa:
 - guardar_token_verificacion(id_usuario: str, token: str) -> None
"""
from urllib.parse import urlencode
from uuid import uuid4
from typing import Optional

class EnviarVerificacionCorreo:
    def __init__(self, repositorio, servicio_correo, app_base_url: str):
        """
        repositorio: instancia de SQLiteRepositorioUsuario (con método guardar_token_verificacion)
        servicio_correo: instancia de GoogleSMTPCliente (con método enviar_email)
        app_base_url: URL base de tu app, p.ej. "http://127.0.0.1:5000"
        """
        self.repositorio = repositorio
        self.servicio_correo = servicio_correo
        self.app_base_url = app_base_url.rstrip("/")

    def _generar_token(self) -> str:
        return uuid4().hex

    def _construir_link_verificacion(self, id_usuario: str, email: str, token: str) -> str:
        params = urlencode({"user": id_usuario, "email": email, "token": token})
        return f"{self.app_base_url}/api/v1/auth/verify?{params}"

    def ejecutar(self, id_usuario: str, email: Optional[str] = None) -> str:
        """
        Genera token, lo guarda y envía el correo. Devuelve el token.
        - id_usuario: id del usuario (string)
        - email: si se pasa, se usará como destino; si no, se obtiene del repositorio (se asume obtener_por_id)
        """
        if email is None:
            # Intentar obtener email desde repo si el repositorio tiene obtener_por_id
            if hasattr(self.repositorio, "obtener_por_id"):
                u = self.repositorio.obtener_por_id(id_usuario)
                if not u or not getattr(u, "email", None):
                    raise ValueError("No se encontró el email del usuario.")
                email = u.email
            else:
                raise ValueError("Se requiere email para enviar verificación.")

        token = self._generar_token()

        # Guardar token en repo (debe existir este método en tu repositorio)
        if hasattr(self.repositorio, "guardar_token_verificacion"):
            self.repositorio.guardar_token_verificacion(id_usuario=id_usuario, token=token)
        else:
            # Si no existe el método, intenta asignarlo directamente (no recomendado)
            raise RuntimeError("El repositorio no implementa guardar_token_verificacion")

        # Construir link y cuerpo del correo
        link = self._construir_link_verificacion(id_usuario=id_usuario, email=email, token=token)
        asunto = "Verifica tu cuenta - Librería Jehová Jiréh"
        html = f"""
        <html>
          <body>
            <p>Hola,</p>
            <p>Gracias por crear una cuenta en Librería Jehová Jiréh. Haz clic en el enlace siguiente para verificar tu correo:</p>
            <p><a href="{link}">Verificar mi cuenta</a></p>
            <p>Si no solicitaste esto, ignora este mensaje.</p>
            <hr>
            <p style="font-size:.85em;color:#666">Si el enlace no funciona, copia y pega esta URL en tu navegador:<br/>{link}</p>
          </body>
        </html>
        """
        texto_plano = f"Verifica tu cuenta: {link}"

        # Envío (puede lanzar excepciones si SMTP falla)
        self.servicio_correo.enviar_email(para=email, asunto=asunto, html=html, texto_plano=texto_plano)

        return token
