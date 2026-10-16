"""
Rotas de Backup, Restauração e Exportação para o Fifine AmpliGame D6 Studio Server.
Garante proteção com backup golden e importação/exportação atômica de perfis.
"""

from .router import Router


def register_backup_routes(router: Router):

    @router.get("/api/backup/export")
    def export_backup(handler, engine, query):
        router.send_json(handler, 200, engine.config)

    @router.post("/api/backup/restore_golden")
    def restore_golden_backup(handler, engine, body):
        ok = engine.restore_golden_backup()
        router.send_json(handler, 200, {"success": ok})

    @router.post("/api/backup/import_full")
    def import_full_backup(handler, engine, body):
        config_data = body.get("config")
        if config_data and isinstance(config_data, dict) and "pages" in config_data:
            engine.config = config_data
            engine.save_config()
            engine.sync_all_keys()
            router.send_json(handler, 200, {"success": True, "pages_count": len(config_data.get("pages", {}))})
        else:
            router.send_json(handler, 400, {"success": False, "error": "Formato de arquivo de backup inválido"})
