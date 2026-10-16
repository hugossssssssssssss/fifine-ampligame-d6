"""
Rotas de Sistema e Hardware para o Fifine AmpliGame D6 Studio Server.
Gerencia status, conexão, brilho, rotação, suspensão/despertar e auto-switch de aplicativos macOS.
"""

import os
import time
import subprocess
from .router import Router


def register_system_routes(router: Router):

    @router.get("/api/state")
    def get_state(handler, engine, query):
        now = time.time()
        if now - getattr(engine, "_last_profile_sync_ts", 0) > 30.0:
            engine._last_profile_sync_ts = now
            try:
                engine.sync_with_native_profiles()
            except Exception as e:
                print(f"[Server] Erro no sync de perfis: {e}")

        data = {
            "connected": engine.is_connected(),
            "brightness": engine.config.get("brightness", 80),
            "active_page": engine.config.get("active_page", "principal"),
            "auto_switch_enabled": engine.config.get("auto_switch_enabled", True),
            "frontmost_app": engine.get_frontmost_app(),
            "screen_off_seconds": engine.config.get("screen_off_seconds", 0),
            "led_sleep_follow": engine.config.get("led_sleep_follow", True),
            "rotation": engine.config.get("rotation", 0),
            "is_asleep": getattr(engine, "is_asleep", False),
            "idle_seconds": int(time.time() - getattr(engine, "_last_activity_time", time.time())),
            "last_pressed_slot": getattr(engine, "_last_pressed_slot", None),
            "last_pressed_ts": getattr(engine, "_last_pressed_ts", 0.0),
            "pages": engine.config.get("pages", {})
        }
        router.send_json(handler, 200, data)

    @router.get("/api/press_events")
    def get_press_events(handler, engine, query):
        """Retorna eventos de toque em teclas físicas para animação sincronizada na Web UI."""
        since = float(query.get("since", [0])[0]) if "since" in query else 0.0
        last_ts = getattr(engine, "_last_pressed_ts", 0.0)
        last_slot = getattr(engine, "_last_pressed_slot", None)
        has_new = bool((last_ts > since) and (last_slot is not None))
        router.send_json(handler, 200, {
            "has_new": has_new,
            "slot": last_slot if has_new else None,
            "ts": last_ts
        })

    @router.get("/api/connect")
    def connect_device(handler, engine, query):
        ok = False
        try:
            ok = engine.connect()
        except Exception as e:
            print(f"[Server] Erro ao reconectar hardware: {e}")
        router.send_json(handler, 200, {"success": ok, "connected": engine.is_connected()})

    @router.get("/api/browse_app")
    def browse_apps(handler, engine, query):
        apps = []
        seen = set()
        search_dirs = [
            "/Applications",
            "/System/Applications",
            "/System/Applications/Utilities",
            os.path.expanduser("~/Applications"),
            os.path.expanduser("~/Downloads"),
            "/Applications/Utilities"
        ]
        for d in search_dirs:
            if os.path.exists(d):
                try:
                    for f in sorted(os.listdir(d)):
                        if f.endswith(".app"):
                            name = f[:-4]
                            if name not in seen:
                                seen.add(name)
                                apps.append({"name": name, "path": os.path.join(d, f)})
                except Exception:
                    pass
        apps.sort(key=lambda a: a["name"].lower())
        router.send_json(handler, 200, apps)

    @router.get("/api/running_apps")
    def running_apps(handler, engine, query):
        running = []
        try:
            r = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get name of every process whose background only is false'],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0 and r.stdout:
                for name in r.stdout.strip().split(","):
                    clean_name = name.strip()
                    if clean_name and clean_name not in [a["name"] for a in running]:
                        running.append({"name": clean_name})
        except Exception as e:
            print(f"[Server] Erro ao listar running_apps: {e}")
        router.send_json(handler, 200, running)

    @router.post("/api/brightness")
    def set_brightness(handler, engine, body):
        percent = int(body.get("percent", 80))
        engine.set_brightness(percent)
        engine.save_config()
        router.send_json(handler, 200, {"success": True, "brightness": percent})

    @router.post("/api/settings/led_sleep_follow")
    def set_led_sleep_follow(handler, engine, body):
        enabled = bool(body.get("enabled", True))
        engine.config["led_sleep_follow"] = enabled
        engine.save_config()
        router.send_json(handler, 200, {"success": True, "led_sleep_follow": enabled})

    @router.post("/api/screen_off")
    def set_screen_off(handler, engine, body):
        seconds = int(body.get("seconds", 0))
        engine.config["screen_off_seconds"] = seconds
        engine.save_config()
        engine.reset_inactivity()
        router.send_json(handler, 200, {"success": True, "screen_off_seconds": seconds})

    @router.post("/api/device/sleep")
    def device_sleep(handler, engine, body):
        engine.sleep_device()
        router.send_json(handler, 200, {"success": True, "is_asleep": True})

    @router.post("/api/device/wake")
    def device_wake(handler, engine, body):
        engine.wake_device()
        router.send_json(handler, 200, {"success": True, "is_asleep": False})

    @router.post("/api/rotation")
    def set_rotation(handler, engine, body):
        angle = int(body.get("rotation", 0))
        engine.set_rotation(angle)
        router.send_json(handler, 200, {"success": True, "rotation": angle})

    @router.post("/api/autoswitch/toggle")
    def toggle_autoswitch(handler, engine, body):
        enabled = bool(body.get("enabled", True))
        engine.config["auto_switch_enabled"] = enabled
        engine.save_config()
        router.send_json(handler, 200, {"success": True, "auto_switch_enabled": enabled})
