"""
Pacote de Modelos Canônicos de Dados do Fifine AmpliGame D6.
Fornece tipagem forte, contratos claros e validação.
"""

from .action import ActionModel
from .key import KeyModel, KeyVisualModel
from .scene import SceneModel
from .config import ConfigModel, SettingsModel
from .storage import StorageManager

__all__ = [
    "ActionModel",
    "KeyModel",
    "KeyVisualModel",
    "SceneModel",
    "ConfigModel",
    "SettingsModel",
    "StorageManager",
]
