"""
Modelo canônico de Cena / Página / Pasta do Fifine AmpliGame D6.
Gerencia os 15 slots de teclas e vínculos com aplicativos do macOS.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from .key import KeyModel


@dataclass
class SceneModel:
    id: str
    name: str = "Nova Cena"
    is_folder: bool = False
    parent_page: Optional[str] = None
    parent_slot: Optional[int] = None
    linked_app: str = ""
    native_folder: Optional[str] = None
    keys: Dict[str, KeyModel] = field(default_factory=dict)  # "1" a "15"

    @classmethod
    def from_dict(cls, scene_id: str, data: Dict[str, Any]) -> "SceneModel":
        if not data or not isinstance(data, dict):
            return cls(id=scene_id)

        keys_map: Dict[str, KeyModel] = {}
        raw_keys = data.get("keys", {})
        if isinstance(raw_keys, dict):
            for k_str, k_data in raw_keys.items():
                try:
                    slot_int = int(k_str)
                    if 1 <= slot_int <= 18:
                        keys_map[str(slot_int)] = KeyModel.from_dict(slot_int, k_data)
                except ValueError:
                    continue

        return cls(
            id=scene_id,
            name=str(data.get("name") or scene_id),
            is_folder=bool(data.get("is_folder", False)),
            parent_page=data.get("parent_page"),
            parent_slot=data.get("parent_slot"),
            linked_app=str(data.get("linked_app") or ""),
            native_folder=data.get("native_folder"),
            keys=keys_map,
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "keys": {k: v.to_dict() for k, v in self.keys.items()}
        }
        if self.is_folder:
            d["is_folder"] = True
            if self.parent_page: d["parent_page"] = self.parent_page
            if self.parent_slot: d["parent_slot"] = self.parent_slot
        if self.linked_app:
            d["linked_app"] = self.linked_app
        if self.native_folder:
            d["native_folder"] = self.native_folder
        return d
