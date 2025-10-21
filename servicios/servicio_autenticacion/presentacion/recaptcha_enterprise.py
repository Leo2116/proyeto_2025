import os
import requests


def verify_enterprise(recaptcha_token: str, action: str | None = None, request_obj=None):
    """Verify reCAPTCHA Enterprise token using Assessments API.
    Returns (ok: bool, msg: str | None).
    If request_obj is provided (Flask request), remote IP is included.
    """
    from configuracion import Config

    project_id = os.getenv('RECAPTCHA_PROJECT_ID') or getattr(Config, 'RECAPTCHA_PROJECT_ID', None)
    api_key = os.getenv('RECAPTCHA_API_KEY') or getattr(Config, 'RECAPTCHA_API_KEY', None)
    site_key = os.getenv('RECAPTCHA_SITE_KEY') or getattr(Config, 'RECAPTCHA_SITE_KEY', None)
    if not (project_id and api_key and site_key):
        return False, 'Configuración reCAPTCHA Enterprise incompleta.'
    if not recaptcha_token:
        return False, 'Falta verificación reCAPTCHA.'

    url = f'https://recaptchaenterprise.googleapis.com/v1/projects/{project_id}/assessments?key={api_key}'

    user_ip = None
    try:
        if request_obj is not None:
            user_ip = request_obj.headers.get('X-Forwarded-For', request_obj.remote_addr)
    except Exception:
        user_ip = None

    payload = {
        'event': {
            'token': recaptcha_token,
            'siteKey': site_key,
        }
    }
    if action:
        payload['event']['expectedAction'] = action
    if user_ip:
        payload['event']['userIpAddress'] = user_ip

    try:
        r = requests.post(url, json=payload, timeout=10)
        jr = r.json() or {}
        props = jr.get('tokenProperties', {})
        if not props.get('valid', False):
            reason = props.get('invalidReason')
            host = props.get('hostname')
            details = []
            if host:
                details.append(f'hostname={host}')
            if reason:
                details.append(f'invalid={reason}')
            extra = f" ({'; '.join(details)})" if details else ''
            return False, f'reCAPTCHA inválido{extra}.'
        # For checkbox, valid=True is enough; for score-based v3 one may check riskAnalysis.
        return True, None
    except Exception:
        return False, 'No se pudo verificar reCAPTCHA.'

