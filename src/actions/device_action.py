"""
Comandos de Hardware e Ajustes de Dispositivo (Brilho, Sleep, Toggle).
"""

from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel
from .hotkey_action import HotkeyCommand


class BrightnessCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        if not engine:
            return False
        b_val = action.raw.get("brightness")
        if b_val is not None:
            engine.set_brightness(int(b_val))
        else:
            cur = engine.config.get("brightness", 80)
            next_val = (cur + 20) if cur < 100 else 20
            engine.set_brightness(next_val)
        engine.save_config()
        return True


class SleepDeviceCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        if not engine:
            return False
        if getattr(engine, "is_asleep", False):
            engine.wake_device()
        else:
            engine.sleep_device()
        return True


class ToggleStateCommand(ActionCommand):
    """Alternador de estado A/B com atualização de visual na tela LCD."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        cur_state = int(action.current_state)
        next_state = 1 if cur_state == 0 else 0
        action.current_state = next_state

        # Executa atalho ou ação correspondente
        k = action.keys_a if cur_state == 0 else action.keys_b
        if k:
            HotkeyCommand.send_hotkey(str(k))

        # Atualiza visual no hardware imediatamente se o slot for conhecido
        if slot is not None and engine:
            page_id = engine.config.get("active_page", "principal")
            page = engine.config.get("pages", {}).get(page_id, {})
            key_data = page.get("keys", {}).get(str(slot))
            if key_data:
                if next_state == 1:
                    if action.title_b: key_data["title"] = action.title_b
                    if action.bg_b: key_data["bg"] = action.bg_b
                    if action.accent_b: key_data["accent"] = action.accent_b
                else:
                    if action.title_a: key_data["title"] = action.title_a
                    if action.bg_a: key_data["bg"] = action.bg_a
                    if action.accent_a: key_data["accent"] = action.accent_a
                engine.sync_key(slot)
                engine.save_config()

        return True
