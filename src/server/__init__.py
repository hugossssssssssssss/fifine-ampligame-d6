"""
Pacote de Servidor HTTP REST Modular para o Fifine AmpliGame D6 Studio.
"""

from .router import Router
from .routes_system import register_system_routes
from .routes_scenes import register_scenes_routes
from .routes_keys import register_keys_routes
from .routes_obs import register_obs_routes
from .routes_backup import register_backup_routes


def create_app_router() -> Router:
    """Instancia e registra todos os módulos de rotas do Studio Server."""
    router = Router()
    register_system_routes(router)
    register_scenes_routes(router)
    register_keys_routes(router)
    register_obs_routes(router)
    register_backup_routes(router)
    return router


__all__ = ["Router", "create_app_router"]
