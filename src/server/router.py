"""
Mini Roteador HTTP Modular para o Fifine AmpliGame D6 Studio Server.
Permite o registro declarativo de endpoints GET e POST, parse de JSON e respostas unificadas.
"""

import json
import urllib.parse
from typing import Callable, Dict, Any, Tuple


class Router:
    """Roteador para requisições HTTP REST do Studio Server."""

    def __init__(self):
        self._get_routes: Dict[str, Callable] = {}
        self._post_routes: Dict[str, Callable] = {}

    def get(self, path: str):
        """Decorador para registrar endpoints GET."""
        def decorator(fn: Callable):
            self._get_routes[path] = fn
            return fn
        return decorator

    def post(self, path: str):
        """Decorador para registrar endpoints POST."""
        def decorator(fn: Callable):
            self._post_routes[path] = fn
            return fn
        return decorator

    def handle_get(self, handler, engine) -> bool:
        """Executa a rota GET correspondente ao caminho da requisição."""
        parsed = urllib.parse.urlparse(handler.path)
        path = parsed.path
        fn = self._get_routes.get(path)
        if fn:
            query = urllib.parse.parse_qs(parsed.query)
            fn(handler, engine, query)
            return True
        return False

    def handle_post(self, handler, engine) -> bool:
        """Executa a rota POST correspondente ao caminho da requisição."""
        parsed = urllib.parse.urlparse(handler.path)
        path = parsed.path
        fn = self._post_routes.get(path)
        if fn:
            content_length = int(handler.headers.get("Content-Length", 0))
            body_data = {}
            if content_length > 0:
                try:
                    raw_body = handler.rfile.read(content_length)
                    body_data = json.loads(raw_body.decode("utf-8"))
                except Exception as e:
                    print(f"[Router POST Parse Error] {path}: {e}")
            fn(handler, engine, body_data)
            return True
        return False

    @staticmethod
    def send_json(handler, status_code: int, data: Any):
        """Envia resposta JSON padronizada com headers CORS e no-cache."""
        handler.send_response(status_code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    @staticmethod
    def send_bytes(handler, status_code: int, mime: str, data: bytes):
        """Envia dados binários com mime especificado."""
        handler.send_response(status_code)
        handler.send_header("Content-Type", mime)
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(data)
