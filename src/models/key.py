"""
Modelo canônico de Tecla (Slot 1..15) do Fifine AmpliGame D6.
Separa apresentação visual (display LCD) do comportamento executável (Action).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from .action import ActionModel


@dataclass
class KeyVisualModel:
    title: str = ""
    subtitle: str = ""
    bg: str = "#18181b"
    textColor: str = "#ffffff"
    accent: str = "#007aff"
    fontSize: int = 12
    fontFamily: str = "Helvetica"
    bold: bool = False
    italic: bool = False
    underline: bool = False
    titleAlignment: str = "middle"
    showTitle: bool = True
    borderColor: str = ""
    borderWidth: int = 0
    imageFit: str = "cover"
    imagePath: str = ""
    icon: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyVisualModel":
        if not data or not isinstance(data, dict):
            return cls()

        # Aceita fontes em string "12px" ou int 12
        fs = data.get("fontSize", 12)
        if isinstance(fs, str):
            digits = "".join(c for c in fs if c.isdigit())
            fs = int(digits) if digits else 12

        bw = data.get("borderWidth", 0)
        if isinstance(bw, str):
            digits = "".join(c for c in bw if c.isdigit())
            bw = int(digits) if digits else 0

        return cls(
            title=str(data.get("title") or ""),
            subtitle=str(data.get("subtitle") or ""),
            bg=str(data.get("bg") or "#18181b"),
            textColor=str(data.get("textColor") or "#ffffff"),
            accent=str(data.get("accent") or "#007aff"),
            fontSize=int(fs),
            fontFamily=str(data.get("fontFamily") or "Helvetica"),
            bold=bool(data.get("bold", False)),
            italic=bool(data.get("italic", False)),
            underline=bool(data.get("underline", False)),
            titleAlignment=str(data.get("titleAlignment") or "middle"),
            showTitle=bool(data.get("showTitle", True)),
            borderColor=str(data.get("borderColor") or ""),
            borderWidth=int(bw),
            imageFit=str(data.get("imageFit") or "cover"),
            imagePath=str(data.get("imagePath") or ""),
            icon=str(data.get("icon") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "title": self.title,
            "subtitle": self.subtitle,
            "bg": self.bg,
            "textColor": self.textColor,
            "accent": self.accent,
            "fontSize": self.fontSize,
            "fontFamily": self.fontFamily,
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "titleAlignment": self.titleAlignment,
            "showTitle": self.showTitle,
        }
        if self.borderColor: d["borderColor"] = self.borderColor
        if self.borderWidth > 0: d["borderWidth"] = self.borderWidth
        if self.imageFit != "cover": d["imageFit"] = self.imageFit
        if self.imagePath: d["imagePath"] = self.imagePath
        if self.icon: d["icon"] = self.icon
        return d


@dataclass
class KeyModel:
    slot: int  # 1 a 15 (1-indexed canônico)
    visual: KeyVisualModel = field(default_factory=KeyVisualModel)
    action: Optional[ActionModel] = None

    @classmethod
    def from_dict(cls, slot: int, data: Dict[str, Any]) -> "KeyModel":
        if not data or not isinstance(data, dict):
            return cls(slot=slot)

        visual = KeyVisualModel.from_dict(data)

        # Extrai ação aninhada ou converte propriedades soltas
        action_data = data.get("action")
        if not action_data:
            act_type = data.get("actionType") or data.get("type") or data.get("uuid")
            if act_type and act_type != "none":
                action_data = {
                    "type": act_type,
                    "target": data.get("target") or data.get("path") or data.get("url") or "",
                    "path": data.get("path") or "",
                    "text": data.get("textPayload") or data.get("text") or "",
                    "keys": data.get("hotkey") or data.get("keys") or "",
                    "command": data.get("command") or data.get("cmd") or "",
                    "uuid": data.get("uuid") or data.get("actionUuid") or "",
                }

        action = ActionModel.from_dict(action_data) if action_data else None
        return cls(slot=slot, visual=visual, action=action)

    def to_dict(self) -> Dict[str, Any]:
        d = self.visual.to_dict()
        if self.action:
            d["action"] = self.action.to_dict()
        return d
