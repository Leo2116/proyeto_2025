# app.py
from flask import Flask, render_template, jsonify, request, session
import os

from configuracion import Config
from servicios.servicio_catalogo.presentacion.rutas import catalogo_bp
from servicios.servicio_autenticacion.presentacion.rutas import auth_bp  # <- NUEVO
from servicios.api_externa.presentacion.rutas_books import books_bp
from servicios.api_externa.presentacion.rutas_postal import postal_bp
from servicios.chat.presentacion.rutas_chat import chat_bp
from servicios.pagos.presentacion.rutas_pagos import payments_bp

def crear_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
        static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
    )
    app.config.from_object(Config)
    # Por si tu Config no trae SECRET_KEY
    app.config.setdefault("SECRET_KEY", "cambia-esto-por-uno-seguro")

    # Blueprints
    app.register_blueprint(catalogo_bp)  # mantiene tu registro existente
    app.register_blueprint(auth_bp)      # <- NUEVO: /api/v1/auth/*
    app.register_blueprint(books_bp)     # <- NUEVO: /api/v1/books
    app.register_blueprint(postal_bp)    # <- NUEVO: /api/v1/postal/<codigo>
    app.register_blueprint(chat_bp)      # <- NUEVO: /api/v1/chat/recomendar
    app.register_blueprint(payments_bp)  # <- NUEVO: /api/v1/payments/*

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

    @app.errorhandler(404)
    def pagina_no_encontrada(_error):
        return jsonify({"error": "Ruta no encontrada"}), 404

    return app

create_app = crear_app

if __name__ == "__main__":
    app = crear_app()
    print("Iniciando servidor Flask. Accede a http://127.0.0.1:5000/")
    app.run(debug=True)
