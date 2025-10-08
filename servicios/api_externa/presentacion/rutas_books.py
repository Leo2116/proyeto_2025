from flask import Blueprint, request, jsonify
import os

from servicios.api_externa.google_books import buscar_libros


books_bp = Blueprint("books_bp", __name__, url_prefix="/api/v1")


@books_bp.get("/books")
def api_books_search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "Parámetro 'q' es requerido."}), 400

    api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
    try:
        resultados = buscar_libros(q=q, api_key=api_key)
        return jsonify(resultados), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Error al consultar Google Books."}), 502

