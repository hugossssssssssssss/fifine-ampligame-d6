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
            "startup_screen_mode": engine.config.get("startup_screen_mode", "black"),
            "startup_screen_path": engine.config.get("startup_screen_path", ""),
            "autostart_enabled": engine.is_autostart_enabled() if hasattr(engine, "is_autostart_enabled") else False,
            "last_pressed_slot": getattr(engine, "_last_pressed_slot", None),
            "last_pressed_ts": getattr(engine, "_last_pressed_ts", 0.0),
            "pages": engine.config.get("pages", {}),
            "rendered_frames": engine.get_rendered_frames_for_page() if hasattr(engine, "get_rendered_frames_for_page") else {},
            "volume_step": engine.config.get("volume_step", 6.25),
            "blocked_apps": engine.config.get("blocked_apps", []),
            "blocked_sites": engine.config.get("blocked_sites", []),
            "favorite_sites": engine.config.get("favorite_sites", [])
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

    @router.post("/api/cache/purge")
    def purge_cache(handler, engine, body):
        """Limpa teclas vazias/fantasmas em todas as páginas e força o hardware a desligar teclas vazias."""
        active_page = engine.config.get("active_page", "principal")
        pages = engine.config.get("pages", {})
        for p_id, p_data in pages.items():
            if "keys" in p_data:
                clean_keys = {}
                for k, v in list(p_data["keys"].items()):
                    if v and isinstance(v, dict):
                        has_title = bool(str(v.get("title", "")).strip())
                        has_img = bool(str(v.get("imagePath", "")).strip())
                        act = v.get("action", {})
                        has_act = bool(act and (act.get("type") or act.get("target") or act.get("uuid")))
                        has_bg = bool(v.get("bg") and v.get("bg") not in ("#18181b", "#000000", "#252528"))
                        if has_title or has_img or has_act or has_bg:
                            clean_keys[k] = v
                p_data["keys"] = clean_keys
        
        engine._displayed_key_hashes.clear()
        engine.save_config()

        if engine.device:
            for s in range(1, 16):
                try:
                    engine.sync_key(s, force=True, page_id=active_page, refresh_now=False)
                except Exception:
                    pass
            if hasattr(engine.device, "refresh"):
                try:
                    engine.device.refresh()
                except Exception:
                    pass

        router.send_json(handler, 200, {"success": True, "pages": engine.config.get("pages", {})})

    @router.get("/api/startup_screen")
    def get_startup_screen(handler, engine, query):
        """Returns startup screen status and current mode."""
        info = engine.get_startup_screen_info() if hasattr(engine, "get_startup_screen_info") else {
            "mode": engine.config.get("startup_screen_mode", "black"),
            "path": engine.config.get("startup_screen_path", ""),
            "device_connected": engine.is_connected()
        }
        router.send_json(handler, 200, info)

    @router.post("/api/startup_screen")
    def set_startup_screen(handler, engine, body):
        """Sets or resets the startup/standby background screen on the physical device."""
        action = body.get("action", "reset")
        path = body.get("path", None)
        if action == "reset" or not path:
            ok = engine.reset_startup_screen(persist=True)
        else:
            ok = engine.set_startup_screen(path, persist=True)
        info = engine.get_startup_screen_info() if hasattr(engine, "get_startup_screen_info") else {}
        router.send_json(handler, 200, {"success": ok, "info": info})

    @router.get("/api/autostart")
    def get_autostart(handler, engine, query):
        """Returns whether the macOS user LaunchAgent autostart is enabled."""
        enabled = engine.is_autostart_enabled() if hasattr(engine, "is_autostart_enabled") else False
        router.send_json(handler, 200, {"enabled": enabled})

    @router.post("/api/autostart")
    def set_autostart(handler, engine, body):
        """Enables or disables automatic startup on macOS user session login."""
        enabled = bool(body.get("enabled", False))
        ok = engine.set_autostart(enabled) if hasattr(engine, "set_autostart") else False
        is_now_enabled = engine.is_autostart_enabled() if hasattr(engine, "is_autostart_enabled") else False
        router.send_json(handler, 200, {"success": ok, "enabled": is_now_enabled})

    @router.get("/api/audio/devices")
    def get_audio_devices(handler, engine, query):
        """Returns available macOS audio output devices and currently active output."""
        devices = []
        current = ""
        bin_path = "/opt/homebrew/bin/SwitchAudioSource"
        if not os.path.exists(bin_path):
            bin_path = "SwitchAudioSource"
        try:
            out = subprocess.check_output([bin_path, "-a", "-t", "output"], timeout=2).decode().splitlines()
            devices = [d.strip() for d in out if d.strip()]
            current = subprocess.check_output([bin_path, "-c"], timeout=2).decode().strip()
        except Exception as e:
            print(f"[Server] Erro ao listar dispositivos de áudio: {e}")
        router.send_json(handler, 200, {"devices": devices, "current": current})

    @router.get("/api/settings/apps_sites")
    def get_apps_sites_settings(handler, engine, query):
        """Returns installed apps, blocked apps, favorite sites, and blocked sites."""
        # 1. Installed apps
        apps = []
        seen = set()
        search_dirs = [
            "/Applications",
            "/System/Applications",
            "/System/Applications/Utilities",
            os.path.expanduser("~/Applications")
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

        default_favorites = [
            {"name": "GitHub", "url": "https://github.com", "domain": "github.com"},
            {"name": "ChatGPT", "url": "https://chatgpt.com", "domain": "chatgpt.com"},
            {"name": "Claude", "url": "https://claude.ai", "domain": "claude.ai"},
            {"name": "Figma", "url": "https://www.figma.com", "domain": "figma.com"},
            {"name": "Notion", "url": "https://www.notion.so", "domain": "notion.so"},
            {"name": "Reddit", "url": "https://www.reddit.com", "domain": "reddit.com"},
            {"name": "YouTube", "url": "https://www.youtube.com", "domain": "youtube.com"},
            {"name": "WhatsApp", "url": "https://web.whatsapp.com", "domain": "whatsapp.com"},
            {"name": "X", "url": "https://x.com", "domain": "x.com"},
            {"name": "LinkedIn", "url": "https://www.linkedin.com", "domain": "linkedin.com"},
            {"name": "Gemini", "url": "https://gemini.google.com", "domain": "gemini.google.com"},
            {"name": "Netflix", "url": "https://www.netflix.com", "domain": "netflix.com"},
            {"name": "Twitch", "url": "https://www.twitch.tv", "domain": "twitch.tv"},
            {"name": "Mercado Livre", "url": "https://www.mercadolivre.com.br", "domain": "mercadolivre.com.br"},
            {"name": "Spotify", "url": "https://open.spotify.com", "domain": "spotify.com"},
            {"name": "Envato", "url": "https://elements.envato.com", "domain": "envato.com"},
            {"name": "Canva", "url": "https://www.canva.com", "domain": "canva.com"},
            {"name": "Stack Overflow", "url": "https://stackoverflow.com", "domain": "stackoverflow.com"},
        ]

        data = {
            "installed_apps": apps,
            "blocked_apps": engine.config.get("blocked_apps", []),
            "favorite_sites": engine.config.get("favorite_sites", default_favorites),
            "blocked_sites": engine.config.get("blocked_sites", [])
        }
        router.send_json(handler, 200, data)

    @router.post("/api/settings/apps_sites")
    def save_apps_sites_settings(handler, engine, body):
        """Saves blocked apps, favorite sites, and blocked sites configurations."""
        if "blocked_apps" in body and isinstance(body["blocked_apps"], list):
            engine.config["blocked_apps"] = body["blocked_apps"]
        if "favorite_sites" in body and isinstance(body["favorite_sites"], list):
            engine.config["favorite_sites"] = body["favorite_sites"]
        if "blocked_sites" in body and isinstance(body["blocked_sites"], list):
            engine.config["blocked_sites"] = body["blocked_sites"]
        engine.save_config()

        # Trigger dynamic update if engine has updater
        if hasattr(engine, "update_dynamic_row2"):
            try:
                engine.update_dynamic_row2(force=True)
            except Exception:
                pass

        router.send_json(handler, 200, {
            "success": True,
            "blocked_apps": engine.config.get("blocked_apps", []),
            "favorite_sites": engine.config.get("favorite_sites", []),
            "blocked_sites": engine.config.get("blocked_sites", [])
        })

    @router.post("/api/settings/volume_step")
    def set_volume_step(handler, engine, body):
        """Sets the global volume adjustment step percentage (e.g. 2, 5, 6.25, 10)."""
        try:
            step = float(body.get("step", 6.25))
            if step <= 0:
                step = 6.25
        except (ValueError, TypeError):
            step = 6.25
        engine.config["volume_step"] = step
        engine.save_config()
        router.send_json(handler, 200, {"success": True, "volume_step": step})

