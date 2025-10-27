# app.py
from flask import Flask, render_template, jsonify, request, session, current_app, redirect, url_for
from flask_cors import CORS
import logging
import os

from configuracion import Config
from servicios.servicio_catalogo.presentacion.rutas import catalogo_bp
from servicios.servicio_autenticacion.presentacion.rutas import auth_bp  # <- NUEVO
from servicios.api_externa.presentacion.rutas_books import books_bp
from servicios.api_externa.presentacion.rutas_postal import postal_bp
from servicios.pagos.presentacion.rutas_pagos import payments_bp
from servicios.facturacion.presentacion.rutas_facturas import facturas_bp
from servicios.ia.presentacion.rutas_llm import ia_bp
from servicios.ia.presentacion.rutas_gemini_ping import ai_dev_bp
from servicios.admin.presentacion.rutas_admin import admin_bp

def crear_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
        static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
    )
    # Habilitar CORS para la API
    # Si necesitas probar desde un dominio distinto, define CORS_ORIGINS
    # como lista separada por comas: "https://mi-frontend.com,https://otro.com"
    cors_env = os.getenv("CORS_ORIGINS", "*")
    allowed = [o.strip() for o in cors_env.split(",") if o.strip()] if cors_env and cors_env != "*" else "*"
    CORS(app, resources={r"/api/*": {"origins": allowed}}, supports_credentials=True)
    
    # Logging básico para producción (Render)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))
    app.config.from_object(Config)
    # Por si tu Config no trae SECRET_KEY
    app.config.setdefault("SECRET_KEY", "cambia-esto-por-uno-seguro")
    # Evitar redirecciones 308/301 automáticas por barra final en rutas
    # (permite acceder con y sin "/" al final sin redirigir)
    try:
        app.url_map.strict_slashes = False
    except Exception:
        pass

    # Hacer disponible la configuración en todas las plantillas (p.ej. reCAPTCHA SITE KEY)
    @app.context_processor
    def inject_config():
        return {"config": app.config}

    # Blueprints
    app.register_blueprint(catalogo_bp)  # mantiene tu registro existente
    app.register_blueprint(auth_bp)      # <- NUEVO: /api/v1/auth/*
    app.register_blueprint(books_bp)     # <- NUEVO: /api/v1/books
    app.register_blueprint(postal_bp)    # <- NUEVO: /api/v1/postal/<codigo>
    # chat recomendado deshabilitado: usar solo IA (/api/v1/ia/*)
    app.register_blueprint(payments_bp)  # <- NUEVO: /api/v1/payments/*
    app.register_blueprint(facturas_bp)  # <- NUEVO: /api/v1/facturas
    app.register_blueprint(ia_bp)        # <- NUEVO: /api/v1/ia/*
    app.register_blueprint(ai_dev_bp)    # <- NUEVO: /api/v1/ai/gemini-ping
    app.register_blueprint(admin_bp)     # <- NUEVO: /api/v1/admin/*

    # ----------------- Carrito -----------------
    def get_cart():
        return session.setdefault("cart", {})

    @app.get("/api/v1/cart")
    def cart_get():
        return jsonify(get_cart()), 200

    @app.post("/api/v1/cart/add")
    def cart_add():
        data = request.get_json(force=True, silent=True) or {}
        pid = data.get("id")
        if not pid:
            return jsonify({"ok": False, "error": "Falta id"}), 400
        name = data.get("nombre", "Producto")
        price = float(data.get("precio", 0))
        img = data.get("portada_url")
        qty = int(data.get("cantidad", 1))

        cart = get_cart()
        if pid in cart:
            cart[pid]["cantidad"] += qty
        else:
            cart[pid] = {"id": pid, "nombre": name, "precio": price, "portada_url": img, "cantidad": qty}
        session["cart"] = cart
        return jsonify({"ok": True, "cart": cart}), 200

    @app.post("/api/v1/cart/update")
    def cart_update():
        data = request.get_json(force=True, silent=True) or {}
        pid = data.get("id")
        qty = int(data.get("cantidad", 1))
        cart = get_cart()
        if pid not in cart:
            return jsonify({"ok": False, "error": "No existe en carrito"}), 404
        if qty <= 0:
            cart.pop(pid)
        else:
            cart[pid]["cantidad"] = qty
        session["cart"] = cart
        return jsonify({"ok": True, "cart": cart}), 200

    @app.post("/api/v1/cart/remove")
    def cart_remove():
        data = request.get_json(force=True, silent=True) or {}
        pid = data.get("id")
        cart = get_cart()
        cart.pop(pid, None)
        session["cart"] = cart
        return jsonify({"ok": True, "cart": cart}), 200

    @app.post("/api/v1/cart/clear")
    def cart_clear():
        session["cart"] = {}
        return jsonify({"ok": True, "cart": {}}), 200

    # ----------------- Rutas base -----------------
    @app.route("/")
    def index():
        return render_template("index.html")

    # Vista simple para administración (protegida por email de admin)
    @app.route("/admin-old")
    def admin_page():
        from configuracion import Config
        email = (session.get("user_email") or "").lower().strip()
        if not email or email not in (Config.ADMIN_EMAILS or []):
            return jsonify({"error": "No autorizado"}), 403
        return render_template("admin.html")

    # ---- Admin: vistas HTML separadas ----
    def _is_admin_session() -> bool:
        try:
            from configuracion import Config as _Cfg
        except Exception:
            return False
        email = (session.get("user_email") or "").lower().strip()
        return bool(email and (email in (getattr(_Cfg, "ADMIN_EMAILS", []) or [])))

    @app.route("/admin")
    def admin_root():
        if not _is_admin_session():
            return jsonify({"error": "No autorizado"}), 403
        return redirect(url_for("admin_productos_view"))

    @app.route("/admin/productos")
    def admin_productos_view():
        if not _is_admin_session():
            return jsonify({"error": "No autorizado"}), 403
        return render_template("admin_productos.html")

    @app.route("/admin/pos")
    def admin_pos_view():
        if not _is_admin_session():
            return jsonify({"error": "No autorizado"}), 403
        return render_template("admin_pos.html")

    @app.route("/admin/tickets")
    def admin_tickets_view():
        if not _is_admin_session():
            return jsonify({"error": "No autorizado"}), 403
        return render_template("admin_tickets.html")

    @app.route("/admin/ventas")
    def admin_ventas_view():
        if not _is_admin_session():
            return jsonify({"error": "No autorizado"}), 403
        return render_template("admin_ventas.html")

    @app.errorhandler(404)
    def pagina_no_encontrada(_error):
        return jsonify({"error": "Ruta no encontrada"}), 404

    @app.errorhandler(Exception)
    def _unhandled(e):
        try:
            current_app.logger.exception("Unhandled")
        except Exception:
            pass
        return {"ok": False, "error": "server_error"}, 500

    return app

create_app = crear_app

if __name__ == "__main__":
    app = crear_app()
    print("Iniciando servidor Flask. Accede a http://127.0.0.1:5000/")
    app.run(debug=True)
