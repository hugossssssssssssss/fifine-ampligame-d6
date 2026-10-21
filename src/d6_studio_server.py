#!/usr/bin/env python3
"""
Fifine AmpliGame D6 Studio Server
Servidor HTTP leve com arquitetura modular desacoplada para a interface Web do Stream Deck.
"""

import sys
import os
import time
import socket
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Importações internas do projeto
from d6_engine import D6Engine
from server import create_app_router

PORT = 5151
STUDIO_DIR = Path(__file__).resolve().parent / "studio"


class FastThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def server_bind(self):
        super().server_bind()
        try:
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass


class StudioHandler(SimpleHTTPRequestHandler):
    engine: D6Engine = None
    router = create_app_router()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STUDIO_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        if self.engine:
            self.engine._last_web_activity_time = time.time()

        # Despacho para o roteador modular REST
        if self.router.handle_get(self, self.engine):
            return

        # Fallback para arquivos estáticos da Web UI (HTML, CSS, JS, Imagens)
        super().do_GET()

    def do_POST(self):
        if self.engine:
            self.engine.reset_inactivity()
            self.engine._last_web_activity_time = time.time()
            if getattr(self.engine, "is_asleep", False):
                self.engine.wake_device()

        # Despacho para o roteador modular REST
        if self.router.handle_post(self, self.engine):
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_studio(auto_open: bool = True):
    engine = D6Engine()
    connected = engine.connect()
    if connected:
        engine.sync_all_keys()
    engine.start_background_telemetry()

    StudioHandler.engine = engine
    server = FastThreadingHTTPServer(("127.0.0.1", PORT), StudioHandler)

    url = f"http://127.0.0.1:{PORT}"
    print("\n=======================================================")
    print("  Fifine AmpliGame D6 Studio - Interface Web Ativa")
    print("=======================================================")
    print(f"• URL: {url}")
    print(f"• Hardware Conectado: {'SIM (Pronto)' if connected else 'NÃO (Plugue via USB e clique Conectar)'}")
    print("• Servidor modular desacoplado (router + routes_*)")
    print("• Pressione Ctrl+C para encerrar o servidor.\n")

    if auto_open:
        import subprocess
        subprocess.Popen(["open", url])

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando Studio Server...")
        engine.close()
        server.server_close()


if __name__ == "__main__":
    run_studio(auto_open=True)
