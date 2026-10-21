"""
Rotas de Teclas, Ícones, Murais e Ações Rápidas para o Fifine AmpliGame D6 Studio Server.
Gerencia atualização de teclas, execução remota, upload de ícones/imagens e áudio.
"""

import os
import time
import base64
import urllib.parse
from pathlib import Path
from .router import Router


def register_keys_routes(router: Router):

    @router.get("/api/image")
    def serve_image(handler, engine, query):
        img_path = query.get("path", [""])[0]
        if img_path and not os.path.isabs(img_path):
            cand = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "studio", img_path))
            if os.path.exists(cand):
                img_path = cand
        if img_path and os.path.exists(img_path) and os.path.isfile(img_path):
            ext = Path(img_path).suffix.lower()
            mime = "image/png"
            if ext in [".jpg", ".jpeg"]:
                mime = "image/jpeg"
            elif ext == ".gif":
                mime = "image/gif"
            elif ext == ".svg":
                mime = "image/svg+xml"

            try:
                with open(img_path, "rb") as f:
                    content = f.read()
                router.send_bytes(handler, 200, mime, content)
            except Exception as e:
                print(f"[Server Image Error] {e}")
                handler.send_response(500)
                handler.end_headers()
        else:
            handler.send_response(404)
            handler.end_headers()


    @router.get("/api/icon_packs")
    def get_icon_packs(handler, engine, query):
        packs = engine.get_icon_packs()
        router.send_json(handler, 200, packs)

    @router.get("/api/skins")
    def get_skins(handler, engine, query):
        skins = engine.get_skins()
        router.send_json(handler, 200, skins)

    @router.get("/api/deck/rendered_frames")
    def get_deck_rendered_frames(handler, engine, query):
        page_id = query.get("page", [engine.config.get("active_page", "principal")])[0]
        frames = engine.get_rendered_frames_for_page(page_id)
        router.send_json(handler, 200, {"page": page_id, "frames": frames})

    @router.get("/api/key/rendered")
    def get_key_rendered(handler, engine, query):
        import io
        page_id = query.get("page", [engine.config.get("active_page", "principal")])[0]
        slot = query.get("slot", ["1"])[0]
        page = engine.config.get("pages", {}).get(page_id, {})
        k_data = page.get("keys", {}).get(str(slot), {})
        try:
            img = engine.render_key_image(k_data)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            router.send_bytes(handler, 200, "image/jpeg", buf.getvalue())
        except Exception as e:
            router.send_json(handler, 500, {"error": str(e)})

    @router.post("/api/key/preview")
    def preview_key(handler, engine, body):
        import io
        import base64
        k_data = body.get("key_data") or body.get("data") or {}
        try:
            img = engine.render_key_image(k_data)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            router.send_json(handler, 200, {"success": True, "frame": f"data:image/jpeg;base64,{b64}"})
        except Exception as e:
            router.send_json(handler, 500, {"success": False, "error": str(e)})

    @router.post("/api/key/update")
    def update_key(handler, engine, body):
        page = body.get("page", engine.config.get("active_page", "principal"))
        key_num = str(body.get("key"))
        key_data = body.get("data")

        if page in engine.config.get("pages", {}):
            if key_data is None:
                page_keys = engine.config["pages"][page].get("keys", {})
                page_keys.pop(str(key_num), None)
                try:
                    page_keys.pop(int(key_num), None)
                except Exception:
                    pass
                try:
                    slot_int = int(key_num)
                    hw_key = engine.get_hw_key_for_slot(slot_int)
                    engine._displayed_key_hashes.pop(hw_key, None)
                    engine.sync_key(slot_int, force=True, page_id=page)
                    engine.remove_key_from_native_manifest(page, slot_int)
                except Exception as e:
                    print(f"[Server] Erro ao limpar tecla física {key_num}: {e}")
            else:
                if "keys" not in engine.config["pages"][page]:
                    engine.config["pages"][page]["keys"] = {}
                engine.config["pages"][page]["keys"][key_num] = key_data
                try:
                    slot_int = int(key_num)
                    engine.sync_key(slot_int, force=True, page_id=page)
                except Exception as e:
                    print(f"[Server] Erro ao sincronizar tecla {key_num}: {e}")

            # Se o usuário está editando teclas desta página na Web UI, garante que ela é a página ativa no Stream Deck
            engine.config["active_page"] = page
            engine._last_manual_page = page
            engine._auto_switched = False
            engine.save_config()

            router.send_json(handler, 200, {"success": True, "page": page, "key": key_num})
        else:
            router.send_json(handler, 400, {"success": False, "error": "Página não encontrada"})

    @router.post("/api/key/delete")
    def delete_key_endpoint(handler, engine, body):
        page = body.get("page", engine.config.get("active_page", "principal"))
        key_num = str(body.get("key"))
        if page in engine.config.get("pages", {}):
            page_keys = engine.config["pages"][page].get("keys", {})
            page_keys.pop(str(key_num), None)
            try:
                page_keys.pop(int(key_num), None)
            except Exception:
                pass
            engine.save_config()
            try:
                slot_int = int(key_num)
                hw_key = engine.get_hw_key_for_slot(slot_int)
                engine._displayed_key_hashes.pop(hw_key, None)
                engine.sync_key(slot_int, force=True, page_id=page)
                engine.remove_key_from_native_manifest(page, slot_int)
            except Exception as e:
                print(f"[Server] Erro ao limpar tecla física {key_num}: {e}")
            router.send_json(handler, 200, {"success": True, "page": page, "key": key_num})
        else:
            router.send_json(handler, 400, {"success": False, "error": "Página não encontrada"})

    @router.post("/api/key/execute")
    def execute_key(handler, engine, body):
        slot = body.get("slot")
        action = body.get("action")
        if not action and slot:
            page = engine.config.get("pages", {}).get(engine.config.get("active_page"), {})
            key_data = page.get("keys", {}).get(str(slot))
            if key_data and "action" in key_data:
                action = key_data["action"]
        if action:
            if slot:
                try:
                    s_int = int(slot)
                    engine._last_pressed_slot = s_int
                    engine._last_pressed_ts = time.time()
                    engine.animate_key_press(s_int)
                except Exception:
                    pass
            engine.execute_action(action, slot=slot)
        router.send_json(handler, 200, {"success": True})

    @router.post("/api/folder/create")
    def create_folder(handler, engine, body):
        folder_id = body.get("folder_id", "").strip().lower()
        folder_name = body.get("folder_name", "Submenu")
        parent_page = body.get("parent_page", engine.config.get("active_page", "principal"))
        slot = body.get("slot")

        if not folder_id:
            folder_id = f"pasta_{int(time.time())}"

        if folder_id not in engine.config.get("pages", {}):
            native_folder = engine.create_native_profile(folder_name, folder_id)
            engine.config["pages"][folder_id] = {
                "name": folder_name,
                "parent": parent_page,
                "native_folder": native_folder,
                "keys": {
                    "1": {
                        "title": "VOLTAR",
                        "subtitle": "Menu",
                        "bg": "#18181b",
                        "textColor": "#ffffff",
                        "accent": "#6366f1",
                        "fontSize": 12,
                        "icon": "arrow-left",
                        "action": {
                            "type": "backtoparent",
                            "uuid": "com.hotspot.streamdock.profile.backtoparent",
                            "target": parent_page
                        }
                    }
                }
            }

        if slot and parent_page in engine.config.get("pages", {}):
            s_str = str(slot)
            if "keys" not in engine.config["pages"][parent_page]:
                engine.config["pages"][parent_page]["keys"] = {}
            engine.config["pages"][parent_page]["keys"][s_str] = {
                "title": folder_name.upper()[:10],
                "subtitle": "Pasta",
                "bg": "#1e1e2e",
                "textColor": "#ffffff",
                "accent": "#f59e0b",
                "fontSize": 12,
                "icon": "folder",
                "action": {
                    "type": "openchild",
                    "uuid": "com.hotspot.streamdock.profile.openchild",
                    "target": folder_id
                }
            }
            if engine.config.get("active_page") == parent_page:
                engine.sync_key(slot)

        engine.save_config()
        router.send_json(handler, 200, {"success": True, "folder_id": folder_id, "parent_page": parent_page, "slot": slot})

    @router.post("/api/skin/apply")
    def apply_skin(handler, engine, body):
        skin_id = body.get("skin")
        pid = body.get("page")
        ok = engine.apply_skin(skin_id, pid)
        router.send_json(handler, 200, {"success": ok})

    @router.post("/api/deck/sync")
    def deck_sync(handler, engine, body):
        engine.sync_all_keys()
        router.send_json(handler, 200, {"success": True})

    @router.post("/api/mapping")
    def set_mapping(handler, engine, body):
        idx = int(body.get("index", 0))
        engine.set_mapping_preset(idx)
        router.send_json(handler, 200, {"success": True, "preset": idx})

    @router.post("/api/audio/stop")
    def stop_audio(handler, engine, body):
        for proc in getattr(engine, "_audio_processes", []):
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        engine._audio_processes = []
        router.send_json(handler, 200, {"success": True})

    @router.post("/api/wallpaper/mural")
    def apply_wallpaper_mural(handler, engine, body):
        pid = body.get("page", engine.config.get("active_page", "principal"))
        img_path = body.get("path")
        b64_data = body.get("base64")

        if b64_data:
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64_data)
            temp_wall = f"/tmp/wallpaper_upload_{int(time.time())}.jpg"
            with open(temp_wall, "wb") as f_w:
                f_w.write(raw_bytes)
            img_path = temp_wall

        if img_path and os.path.exists(img_path):
            ok = engine.apply_wallpaper_mural(img_path, pid)
            router.send_json(handler, 200, {"success": ok})
        else:
            router.send_json(handler, 400, {"success": False, "error": "Imagem do papel de parede não encontrada"})

    @router.post("/api/upload_image")
    def upload_image(handler, engine, body):
        fname = body.get("filename", "image.png")
        b64_data = body.get("base64", "")
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        try:
            raw_bytes = base64.b64decode(b64_data)
            icons_dir = Path(__file__).resolve().parent.parent / "studio" / "icons"
            icons_dir.mkdir(parents=True, exist_ok=True)
            safe_name = f"{int(time.time())}_{Path(fname).name}"
            dest = icons_dir / safe_name
            with open(dest, "wb") as f_up:
                f_up.write(raw_bytes)
            url = f"/api/image?path={urllib.parse.quote(str(dest))}"
            router.send_json(handler, 200, {"success": True, "path": str(dest), "url": url})
        except Exception as e:
            router.send_json(handler, 500, {"success": False, "error": str(e)})
