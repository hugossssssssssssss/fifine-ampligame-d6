"""
Modelo canônico de ação (Command Pattern) para o Fifine AmpliGame D6.
Padroniza todas as intenções de execução do hardware e interface web.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ActionModel:
    type: str = "none"
    uuid: str = ""
    target: str = ""
    path: str = ""
    text: str = ""
    keys: str = ""
    command: str = ""
    url: str = ""
    enter: bool = False
    clipboard: bool = True
    delay: float = 0.0
    steps: List[Dict[str, Any]] = field(default_factory=list)
    sceneName: str = ""
    sourceName: str = ""
    sceneItemId: Optional[int] = None
    visible: bool = True
    current_state: int = 0
    title_a: str = ""
    title_b: str = ""
    keys_a: str = ""
    keys_b: str = ""
    bg_a: str = ""
    bg_b: str = ""
    accent_a: str = ""
    accent_b: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["ActionModel"]:
        if not data or not isinstance(data, dict):
            return None

        # Suporta dados legados aninhados em Settings
        settings = data.get("Settings", {}) if isinstance(data.get("Settings"), dict) else {}

        raw_type = data.get("type") or data.get("uuid") or settings.get("type") or "none"
        raw_uuid = data.get("uuid") or data.get("actionUuid") or ""

        target = (
            data.get("target")
            or data.get("path")
            or data.get("url")
            or data.get("app")
            or settings.get("path")
            or settings.get("target")
            or settings.get("url")
            or ""
        )

        return cls(
            type=str(raw_type).strip(),
            uuid=str(raw_uuid).strip(),
            target=str(target).strip(),
            path=str(data.get("path") or settings.get("path") or target).strip(),
            text=str(data.get("text") or data.get("textPayload") or data.get("password") or settings.get("text") or ""),
            keys=str(data.get("keys") or data.get("hotkey") or settings.get("keys") or "").strip(),
            command=str(data.get("command") or data.get("cmd") or "").strip(),
            url=str(data.get("url") or settings.get("url") or "").strip(),
            enter=bool(data.get("enter", False)),
            clipboard=bool(data.get("clipboard", True)),
            delay=float(data.get("delay", 0.0)),
            steps=data.get("steps", []) if isinstance(data.get("steps"), list) else [],
            sceneName=str(data.get("sceneName") or data.get("scene") or ""),
            sourceName=str(data.get("sourceName") or data.get("source") or data.get("input") or ""),
            sceneItemId=data.get("sceneItemId"),
            visible=bool(data.get("visible", True)),
            current_state=int(data.get("current_state", 0)),
            title_a=str(data.get("title_a", "")),
            title_b=str(data.get("title_b", "")),
            keys_a=str(data.get("keys_a", "")),
            keys_b=str(data.get("keys_b", "")),
            bg_a=str(data.get("bg_a", "")),
            bg_b=str(data.get("bg_b", "")),
            accent_a=str(data.get("accent_a", "")),
            accent_b=str(data.get("accent_b", "")),
            raw=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"type": self.type}
        if self.uuid: d["uuid"] = self.uuid
        if self.target: d["target"] = self.target
        if self.path and self.path != self.target: d["path"] = self.path
        if self.text:
            d["text"] = self.text
            d["enter"] = self.enter
            d["clipboard"] = self.clipboard
        if self.keys: d["keys"] = self.keys
        if self.command: d["command"] = self.command
        if self.url: d["url"] = self.url
        if self.delay > 0: d["delay"] = self.delay
        if self.steps: d["steps"] = self.steps
        if self.sceneName: d["sceneName"] = self.sceneName
        if self.sourceName: d["sourceName"] = self.sourceName
        if self.sceneItemId is not None: d["sceneItemId"] = self.sceneItemId
        if not self.visible: d["visible"] = False
        if self.type in ("toggle", "hotkeyswitch"):
            d["current_state"] = self.current_state
            if self.title_a: d["title_a"] = self.title_a
            if self.title_b: d["title_b"] = self.title_b
            if self.keys_a: d["keys_a"] = self.keys_a
            if self.keys_b: d["keys_b"] = self.keys_b
            if self.bg_a: d["bg_a"] = self.bg_a
            if self.bg_b: d["bg_b"] = self.bg_b
            if self.accent_a: d["accent_a"] = self.accent_a
            if self.accent_b: d["accent_b"] = self.accent_b
        return d
