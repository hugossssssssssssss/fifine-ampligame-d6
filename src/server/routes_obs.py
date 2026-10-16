"""
Rotas de Integração com OBS Studio v5 para o Fifine AmpliGame D6 Studio Server.
Gerencia status WebSocket, conexão, alteração de configurações e disparo de ações OBS.
"""

import time
from .router import Router


def register_obs_routes(router: Router):

    @router.get("/api/obs/status")
    def get_obs_status(handler, engine, query):
        obs = getattr(engine, "obs", None)
        if obs:
            data = {
                "connected": obs.connected,
                "identified": obs.identified,
                "host": obs.host,
                "port": obs.port,
                "is_recording": obs.is_recording,
                "is_streaming": obs.is_streaming,
                "is_virtualcam": obs.is_virtualcam,
                "is_studiomode": obs.is_studiomode,
                "current_scene": obs.current_scene,
                "scenes": obs.scenes,
                "audio_inputs": obs.audio_inputs
            }
        else:
            data = {
                "connected": False,
                "identified": False,
                "host": "127.0.0.1",
                "port": 4455,
                "is_recording": False,
                "is_streaming": False,
                "is_virtualcam": False,
                "is_studiomode": False,
                "current_scene": "",
                "scenes": [],
                "audio_inputs": {}
            }
        router.send_json(handler, 200, data)

    @router.post("/api/obs/config")
    def set_obs_config(handler, engine, body):
        host = body.get("host", "127.0.0.1")
        port = int(body.get("port", 4455))
        password = body.get("password", "")
        if not engine.config.get("obs"):
            engine.config["obs"] = {}
        engine.config["obs"]["host"] = host
        engine.config["obs"]["port"] = port
        engine.config["obs"]["password"] = password
        engine.save_config()
        if hasattr(engine, "obs") and engine.obs:
            engine.obs.update_config(host, port, password)
        router.send_json(handler, 200, {"success": True, "host": host, "port": port})

    @router.post("/api/obs/connect")
    def connect_obs(handler, engine, body):
        if hasattr(engine, "obs") and engine.obs:
            engine.obs.connect()
            for _ in range(10):
                if engine.obs.identified:
                    break
                time.sleep(0.1)
            router.send_json(handler, 200, {
                "success": True,
                "connected": engine.obs.connected,
                "identified": engine.obs.identified
            })
        else:
            router.send_json(handler, 400, {"success": False, "error": "OBS client não disponível"})

    @router.post("/api/obs/action")
    def execute_obs_action(handler, engine, body):
        action_type = body.get("action", "")
        data_val = body.get("data", {})
        obs = getattr(engine, "obs", None)
        if obs:
            if action_type == "toggle_record":
                obs.toggle_record()
            elif action_type == "toggle_stream":
                obs.toggle_stream()
            elif action_type == "toggle_virtualcam":
                obs.toggle_virtualcam()
            elif action_type == "toggle_studiomode":
                obs.toggle_studio_mode()
            elif action_type == "set_scene":
                obs.set_current_scene(data_val.get("scene", ""))
            elif action_type == "toggle_mute":
                obs.toggle_audio_mute(data_val.get("source", ""))
            elif action_type == "screenshot":
                obs.trigger_screenshot(data_val.get("scene", ""))
            router.send_json(handler, 200, {"success": True})
        else:
            router.send_json(handler, 400, {"success": False, "error": "OBS não disponível"})
