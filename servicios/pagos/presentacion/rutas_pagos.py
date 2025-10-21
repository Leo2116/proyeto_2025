from flask import Blueprint, request, jsonify

from servicios.pagos.stripe_integration import crear_payment_intent
from servicios.pagos.paypal_integration import crear_orden


payments_bp = Blueprint("payments_bp", __name__, url_prefix="/api/v1/payments")


@payments_bp.post("/stripe/create-payment-intent")
def api_stripe_create_payment_intent():
    data = request.get_json(silent=True) or {}
    total = data.get("total")
    try:
        total = float(total)
    except Exception:
        return jsonify({"error": "'total' debe ser numerico."}), 400

    if total <= 0:
        return jsonify({"error": "El total debe ser mayor a 0."}), 400

    centavos = int(round(total * 100))
    try:
        client_secret = crear_payment_intent(centavos, moneda="gtq")
        return jsonify({"clientSecret": client_secret}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except RuntimeError as re:
        return jsonify({"error": str(re)}), 500
    except Exception:
        return jsonify({"error": "Error al crear PaymentIntent."}), 502


@payments_bp.post("/paypal/create-order")
def api_paypal_create_order():
    data = request.get_json(silent=True) or {}
    total = data.get("total")
    currency = (data.get("currency") or "GTQ").upper()
    try:
        total = float(total)
    except Exception:
        return jsonify({"error": "'total' debe ser numerico."}), 400

    if total <= 0:
        return jsonify({"error": "El total debe ser mayor a 0."}), 400

    try:
        order = crear_orden(total=total, currency=currency)
        approve_url = None
        for link in order.get("links", []) or []:
            if link.get("rel") == "approve":
                approve_url = link.get("href")
                break
        return jsonify({
            "id": order.get("id"),
            "approveUrl": approve_url,
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception:
        return jsonify({"error": "Error al crear orden en PayPal."}), 502
