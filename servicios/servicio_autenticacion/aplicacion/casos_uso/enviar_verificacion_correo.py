"""
Caso de uso: Generar token de verificación, guardarlo en el repositorio y enviar el correo.
Requiere que el repositorio implemente:
 - guardar_token_verificacion(id_usuario: str, token: str) -> None
 - (opcional) obtener_por_id(id_usuario) -> objeto con .email
"""

from urllib.parse import urlencode
from uuid import uuid4
from typing import Optional

try:
    from configuracion import Config
except Exception:
    class Config:  # fallback mínimo
        APP_BASE_URL = "http://127.0.0.1:5000"


class EnviarVerificacionCorreo:
    def __init__(self, repositorio, servicio_correo, app_base_url: Optional[str] = None):
        self.repositorio = repositorio
        self.servicio_correo = servicio_correo
        base = (app_base_url or getattr(Config, "APP_BASE_URL", "http://127.0.0.1:5000"))
        self.app_base_url = (base or "http://127.0.0.1:5000").rstrip("/")

    def _generar_token(self) -> str:
        return uuid4().hex

    def _construir_link_verificacion(self, id_usuario: str, email: str, token: str) -> str:
        params = urlencode({"user": id_usuario, "email": email, "token": token})
        return f"{self.app_base_url}/api/v1/auth/verify?{params}"

    def ejecutar(self, id_usuario: str, email: Optional[str] = None, *_args, **_kwargs) -> str:
        """
        Genera token, lo guarda y envía el correo. Devuelve el token.
        - id_usuario: id del usuario (string)
        - email: si se pasa, se usará como destino; si no, se intenta obtener del repositorio.
        """
        if email is None:
            if hasattr(self.repositorio, "obtener_por_id"):
                u = self.repositorio.obtener_por_id(id_usuario)
                if not u or not getattr(u, "email", None):
                    raise ValueError("No se encontró el email del usuario.")
                email = u.email
            else:
                raise ValueError("Se requiere email para enviar verificación.")

        token = self._generar_token()

        if hasattr(self.repositorio, "guardar_token_verificacion"):
            self.repositorio.guardar_token_verificacion(id_usuario=id_usuario, token=token)
        else:
            raise RuntimeError("El repositorio no implementa guardar_token_verificacion")

        link = self._construir_link_verificacion(id_usuario=id_usuario, email=email, token=token)
        asunto = "Verifica tu cuenta - Librería Jehová Jiréh"
        html = f"""
        <html>
          <body>
            <p>Hola,</p>
            <p>Gracias por crear una cuenta en Librería Jehová Jiréh. Haz clic en el enlace siguiente para verificar tu correo:</p>
            <p><a href=\"{link}\">Verificar mi cuenta</a></p>
            <p>Si no solicitaste esto, ignora este mensaje.</p>
            <hr>
            <p style=\"font-size:.85em;color:#666\">Si el enlace no funciona, copia y pega esta URL en tu navegador:<br/>{link}</p>
          </body>
        </html>
        """
        texto_plano = f"Verifica tu cuenta: {link}"

        # Log útil en desarrollo
        try:
            print(f"[VERIFICACION] Enlace: {link}")
        except Exception:
            pass

        # Compatibilidad con distintos nombres de método en el cliente de correo
        if hasattr(self.servicio_correo, "enviar_email"):
            self.servicio_correo.enviar_email(para=email, asunto=asunto, html=html, texto_plano=texto_plano)
        else:
            self.servicio_correo.enviar_correo(destinatario=email, asunto=asunto, cuerpo_html=html)

        return token
