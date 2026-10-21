"""
Rotas de Gerenciamento de Cenas e Perfis para o Fifine AmpliGame D6 Studio Server.
Permite alternar, criar, duplicar, renomear, vincular aplicativos e importar cenas.
"""

import time
import threading
from .router import Router


def register_scenes_routes(router: Router):

    @router.post("/api/page/select")
    def select_page(handler, engine, body):
        page = body.get("page") or body.get("id") or body.get("profile") or "principal"
        if page in engine.config.get("pages", {}):
            engine.config["active_page"] = page
            threading.Thread(target=lambda: engine.change_page(page), daemon=True).start()
        router.send_json(handler, 200, {"success": True, "active_page": page})

    @router.post("/api/scene/select")
    def select_scene_alias(handler, engine, body):
        return select_page(handler, engine, body)

    @router.post("/api/profile/select")
    def select_profile_alias(handler, engine, body):
        return select_page(handler, engine, body)

    @router.post("/api/page/create")
    def create_page(handler, engine, body):
        page_id = body.get("id", "").strip().lower()
        name = body.get("name", "Nova Página")
        if page_id and page_id not in engine.config.get("pages", {}):
            native_folder = ""
            try:
                native_folder = engine.create_native_profile(name, page_id)
            except Exception as e:
                print(f"[Server] Aviso criação profile nativo: {e}")

            engine.config["pages"][page_id] = {
                "name": name,
                "native_folder": native_folder,
                "keys": {}
            }
            engine.save_config()
            engine.change_page(page_id)
            router.send_json(handler, 200, {"success": True, "id": page_id, "name": name})
        else:
            router.send_json(handler, 400, {"success": False, "error": "Página inválida ou já existente"})

    @router.post("/api/page/delete")
    def delete_page(handler, engine, body):
        page_id = body.get("id")
        if page_id and page_id in engine.config.get("pages", {}) and page_id != "principal":
            ok = engine.delete_page(page_id)
            router.send_json(handler, 200, {"success": ok, "active_page": engine.config.get("active_page", "principal")})
        else:
            router.send_json(handler, 400, {"success": False, "error": "Cena não pode ser excluída"})

    @router.post("/api/profile/rename")
    def rename_profile(handler, engine, body):
        pid = body.get("id")
        new_name = body.get("name")
        ok = engine.rename_page(pid, new_name)
        router.send_json(handler, 200, {"success": ok})

    @router.post("/api/profile/duplicate")
    def duplicate_profile(handler, engine, body):
        pid = body.get("id")
        new_id = engine.duplicate_page(pid)
        router.send_json(handler, 200, {"success": bool(new_id), "new_id": new_id})

    @router.post("/api/profile/link_app")
    def link_app_to_profile(handler, engine, body):
        pid = body.get("id")
        app_name = body.get("app", "").strip()
        if pid and pid in engine.config.get("pages", {}):
            engine.config["pages"][pid]["linked_app"] = app_name
            engine.save_config()
            router.send_json(handler, 200, {"success": True, "id": pid, "linked_app": app_name})
        else:
            router.send_json(handler, 400, {"success": False, "error": "Cena não encontrada"})

    @router.post("/api/profile/import")
    def import_profile(handler, engine, body):
        profile_data = body.get("profile")
        if profile_data and "name" in profile_data:
            pid = f"cena_{int(time.time())}"
            native_folder = engine.create_native_profile(profile_data["name"], pid)
            engine.config["pages"][pid] = {
                "name": profile_data["name"],
                "native_folder": native_folder,
                "keys": profile_data.get("keys", {})
            }
            engine.save_config()
            engine.change_page(pid)
            router.send_json(handler, 200, {"success": True, "id": pid})
        else:
            router.send_json(handler, 400, {"success": False, "error": "Formato de perfil inválido"})
