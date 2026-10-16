#!/usr/bin/env python3
"""
OBS Studio WebSocket v5 Client for Fifine AmpliGame D6
Protocolo oficial OBS WebSocket v5 (RFC padrão, porta 4455, autenticação SHA-256 e eventos ao vivo).
"""

import json
import time
import uuid
import base64
import hashlib
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

try:
    import websocket
except ImportError:
    websocket = None


class OBSClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 4455, password: str = "", auto_reconnect: bool = True):
        self.host = host
        self.port = int(port)
        self.password = password
        self.auto_reconnect = auto_reconnect

        self.ws = None
        self.connected = False
        self.identified = False
        self.running = False

        # Estado vivo do OBS
        self.is_recording = False
        self.is_streaming = False
        self.is_virtualcam = False
        self.is_studiomode = False
        self.current_scene = ""
        self.scenes = []
        self.audio_inputs = {}  # { name: is_muted }

        self._callbacks: List[Callable[['OBSClient'], None]] = []
        self._pending_requests: Dict[str, Dict[str, Any]] = {}
        self._thread = None
        self._lock = threading.Lock()

    def add_state_listener(self, cb: Callable[['OBSClient'], None]):
        """Registra callback chamado quando o status do OBS muda (ex: gravação iniciada)."""
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def _notify_listeners(self):
        for cb in self._callbacks:
            try:
                cb(self)
            except Exception as e:
                print(f"[OBSClient] Erro no callback de listener: {e}")

    def update_config(self, host: str, port: int, password: str):
        changed = (self.host != host or self.port != int(port) or self.password != password)
        self.host = host
        self.port = int(port)
        self.password = password
        if changed and self.running:
            self.disconnect()
            time.sleep(0.5)
            self.connect()

    def connect(self):
        if not websocket:
            print("[OBSClient] websocket-client não instalado.")
            return

        self.running = True
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def disconnect(self):
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.connected = False
        self.identified = False
        self._notify_listeners()

    def _run_loop(self):
        url = f"ws://{self.host}:{self.port}"
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                self.ws.run_forever(ping_interval=10, ping_timeout=5)
            except Exception as e:
                pass

            self.connected = False
            self.identified = False
            self._notify_listeners()

            if self.running and self.auto_reconnect:
                time.sleep(3.0)
            else:
                break

    def _on_open(self, ws):
        self.connected = True
        print(f"[OBSClient] Conectado ao OBS Studio em {self.host}:{self.port} (Aguardando Hello v5)")

    def _on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        self.identified = False
        self._notify_listeners()

    def _on_error(self, ws, error):
        pass

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            op = data.get("op")
            d = data.get("d", {})

            # OpCode 0: Hello do Servidor OBS v5
            if op == 0:
                self._handle_hello(d)

            # OpCode 2: Identified (Conexão Autenticada e Pronta)
            elif op == 2:
                self.identified = True
                print(f"[OBSClient] Identificado com sucesso no OBS Studio v5!")
                self._query_initial_state()
                self._notify_listeners()

            # OpCode 5: Eventos em Tempo Real do OBS
            elif op == 5:
                self._handle_event(data.get("d", {}))

            # OpCode 7: Resposta de Requisição (RequestResponse)
            elif op == 7:
                self._handle_response(d)

        except Exception as e:
            print(f"[OBSClient] Erro ao processar mensagem OBS: {e}")

    def _handle_hello(self, d: Dict[str, Any]):
        auth_info = d.get("authentication")
        auth_response = None

        if auth_info and self.password:
            salt = auth_info.get("salt", "")
            challenge = auth_info.get("challenge", "")
            # RFC OBS v5 Auth:
            # 1. secret = base64(sha256(password + salt))
            secret_hash = hashlib.sha256((self.password + salt).encode("utf-8")).digest()
            secret = base64.b64encode(secret_hash).decode("utf-8")
            # 2. auth_resp = base64(sha256(secret + challenge))
            auth_hash = hashlib.sha256((secret + challenge).encode("utf-8")).digest()
            auth_response = base64.b64encode(auth_hash).decode("utf-8")

        identify = {
            "op": 1,
            "d": {
                "rpcVersion": 1,
                "eventSubscriptions": 1023  # Todos os eventos (General, Scenes, Inputs, Outputs)
            }
        }
        if auth_response:
            identify["d"]["authentication"] = auth_response

        self._send_raw(identify)

    def _query_initial_state(self):
        """Consulta o estado inicial completo de gravação, live, cenas e áudio."""
        self.send_request("GetRecordStatus", cb=self._on_get_record_status)
        self.send_request("GetStreamStatus", cb=self._on_get_stream_status)
        self.send_request("GetVirtualCamStatus", cb=self._on_get_virtualcam_status)
        self.send_request("GetCurrentProgramScene", cb=self._on_get_current_scene)
        self.send_request("GetSceneList", cb=self._on_get_scene_list)
        self.send_request("GetStudioModeEnabled", cb=self._on_get_studiomode)

    def _on_get_record_status(self, resp: Dict[str, Any]):
        self.is_recording = bool(resp.get("outputActive", False))
        self._notify_listeners()

    def _on_get_stream_status(self, resp: Dict[str, Any]):
        self.is_streaming = bool(resp.get("outputActive", False))
        self._notify_listeners()

    def _on_get_virtualcam_status(self, resp: Dict[str, Any]):
        self.is_virtualcam = bool(resp.get("outputActive", False))
        self._notify_listeners()

    def _on_get_current_scene(self, resp: Dict[str, Any]):
        self.current_scene = resp.get("currentProgramSceneName", "")
        self._notify_listeners()

    def _on_get_scene_list(self, resp: Dict[str, Any]):
        scenes = resp.get("scenes", [])
        self.scenes = [s.get("sceneName") for s in scenes if isinstance(s, dict)]
        if resp.get("currentProgramSceneName"):
            self.current_scene = resp.get("currentProgramSceneName")
        self._notify_listeners()

    def _on_get_studiomode(self, resp: Dict[str, Any]):
        self.is_studiomode = bool(resp.get("studioModeEnabled", False))
        self._notify_listeners()

    def _handle_event(self, d: Dict[str, Any]):
        event_type = d.get("eventType")
        event_data = d.get("eventData", {})

        if event_type == "RecordStateChanged":
            self.is_recording = bool(event_data.get("outputActive", False))
            self._notify_listeners()

        elif event_type == "StreamStateChanged":
            self.is_streaming = bool(event_data.get("outputActive", False))
            self._notify_listeners()

        elif event_type == "VirtualcamStateChanged":
            self.is_virtualcam = bool(event_data.get("outputActive", False))
            self._notify_listeners()

        elif event_type in ("CurrentProgramSceneChanged", "CurrentSceneChanged"):
            self.current_scene = event_data.get("sceneName", "")
            self._notify_listeners()

        elif event_type in ("SceneListChanged", "SceneCollectionChanged"):
            self.send_request("GetSceneList", cb=self._on_get_scene_list)

        elif event_type == "InputMuteStateChanged":
            inp = event_data.get("inputName")
            muted = event_data.get("inputMuted")
            if inp:
                self.audio_inputs[inp] = bool(muted)
                self._notify_listeners()

        elif event_type == "StudioModeStateChanged":
            self.is_studiomode = bool(event_data.get("studioModeEnabled", False))
            self._notify_listeners()

    def _handle_response(self, d: Dict[str, Any]):
        req_id = d.get("requestId")
        with self._lock:
            cb_info = self._pending_requests.pop(req_id, None)
        if cb_info:
            cb = cb_info.get("callback")
            resp_data = d.get("responseData", {})
            if cb:
                try:
                    cb(resp_data)
                except Exception as e:
                    print(f"[OBSClient] Erro ao despachar resposta de {req_id}: {e}")

    def _send_raw(self, payload: Dict[str, Any]):
        if self.ws and self.connected:
            try:
                self.ws.send(json.dumps(payload))
            except Exception as e:
                print(f"[OBSClient] Erro de envio WS: {e}")

    def send_request(self, request_type: str, request_data: Optional[Dict[str, Any]] = None, cb: Optional[Callable] = None):
        """Envia uma requisição OpCode 6 para o OBS WebSocket v5."""
        req_id = str(uuid.uuid4())
        payload = {
            "op": 6,
            "d": {
                "requestType": request_type,
                "requestId": req_id,
                "requestData": request_data or {}
            }
        }
        if cb:
            with self._lock:
                self._pending_requests[req_id] = {"callback": cb, "time": time.time()}

        self._send_raw(payload)

    # Métodos de Conveniência para o Hardware e Ações
    def toggle_record(self):
        self.send_request("ToggleRecord")

    def toggle_stream(self):
        self.send_request("ToggleStream")

    def toggle_virtualcam(self):
        self.send_request("ToggleVirtualCam")

    def set_current_scene(self, scene_name: str):
        if scene_name:
            self.send_request("SetCurrentProgramScene", {"sceneName": scene_name})

    def toggle_audio_mute(self, input_name: str):
        if input_name:
            self.send_request("ToggleInputMute", {"inputName": input_name})

    def set_source_visibility(self, scene_name: str, scene_item_id: int, enabled: bool):
        self.send_request("SetSceneItemEnabled", {
            "sceneName": scene_name,
            "sceneItemId": int(scene_item_id),
            "sceneItemEnabled": bool(enabled)
        })

    def toggle_studio_mode(self):
        self.send_request("ToggleStudioMode")

    def trigger_screenshot(self, scene_name: str = ""):
        tgt = scene_name or self.current_scene
        if tgt:
            desktop = str(Path.home() / "Desktop" / f"obs_screenshot_{int(time.time())}.png")
            self.send_request("SaveSourceScreenshot", {
                "sourceName": tgt,
                "imageFormat": "png",
                "imageFilePath": desktop
            })
