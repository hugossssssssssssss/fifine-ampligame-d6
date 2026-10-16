"""
Modelo canônico de Configuração Global do Fifine AmpliGame D6.
Controla o perfil ativo, configurações de brilho, suspensão e dicionário de cenas.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
from .scene import SceneModel


@dataclass
class SettingsModel:
    brightness: int = 100
    rotation: int = 0
    led_sleep_follow: bool = False
    screen_off_seconds: int = 600
    mapping: str = "standard"
    auto_switch_enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SettingsModel":
        return cls(
            brightness=int(data.get("brightness", 100)),
            rotation=int(data.get("rotation", 0)),
            led_sleep_follow=bool(data.get("led_sleep_follow", False)),
            screen_off_seconds=int(data.get("screen_off_seconds", 600)),
            mapping=str(data.get("mapping", "standard")),
            auto_switch_enabled=bool(data.get("auto_switch_enabled", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brightness": self.brightness,
            "rotation": self.rotation,
            "led_sleep_follow": self.led_sleep_follow,
            "screen_off_seconds": self.screen_off_seconds,
            "mapping": self.mapping,
            "auto_switch_enabled": self.auto_switch_enabled,
        }


@dataclass
class ConfigModel:
    active_page: str = "principal"
    settings: SettingsModel = field(default_factory=SettingsModel)
    pages: Dict[str, SceneModel] = field(default_factory=dict)
    version: str = "2.0"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigModel":
        if not data or not isinstance(data, dict):
            data = {}

        # Migração transparente se vier no formato v1 legado
        active = str(data.get("active_page") or "principal")
        settings = SettingsModel.from_dict(data)

        pages_dict: Dict[str, SceneModel] = {}
        raw_pages = data.get("pages", {})
        if isinstance(raw_pages, dict):
            for pid, pdata in raw_pages.items():
                pages_dict[pid] = SceneModel.from_dict(pid, pdata)

        # Garante pelo menos a cena principal
        if "principal" not in pages_dict:
            pages_dict["principal"] = SceneModel(id="principal", name="Cena Padrão")

        if active not in pages_dict:
            active = "principal"

        return cls(
            active_page=active,
            settings=settings,
            pages=pages_dict,
            version=str(data.get("version", "2.0")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Gera o dicionário JSON canônico compatível com versões legadas e modernas."""
        d = self.settings.to_dict()
        d["version"] = self.version
        d["active_page"] = self.active_page
        d["pages"] = {pid: scene.to_dict() for pid, scene in self.pages.items()}
        return d
