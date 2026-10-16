"""
Comando para Envio de Atalhos de Teclado (Hotkeys) no macOS.
Traduz combinações como 'Cmd+Shift+4', 'Ctrl+Alt+T' para chamadas seguras do AppleScript.
"""

import subprocess
from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel


class HotkeyCommand(ActionCommand):
    """Executa atalhos de teclado com modificadores via System Events do macOS."""

    KEY_CODE_MAP = {
        "RETURN": 36, "ENTER": 36, "TAB": 48, "SPACE": 49, "BACKSPACE": 51, "DELETE": 117,
        "ESCAPE": 53, "ESC": 53, "UP": 126, "DOWN": 125, "LEFT": 123, "RIGHT": 124,
        "F1": 122, "F2": 120, "F3": 99, "F4": 118, "F5": 96, "F6": 97,
        "F7": 98, "F8": 100, "F9": 101, "F10": 109, "F11": 103, "F12": 111
    }

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        hotkey_str = action.keys or action.target or ""
        return self.send_hotkey(hotkey_str)

    @classmethod
    def send_hotkey(cls, hotkey_str: str) -> bool:
        if not hotkey_str:
            return False

        raw_str = str(hotkey_str).replace(" - ", "+").replace("-", "+")
        parts = [p.strip() for p in raw_str.split("+") if p.strip()]
        modifiers = []
        main_key = ""

        for p in parts:
            p_up = p.upper()
            if p_up in ("CMD", "COMMAND"):
                modifiers.append("command down")
            elif p_up in ("CTRL", "CONTROL"):
                modifiers.append("control down")
            elif p_up in ("ALT", "OPTION"):
                modifiers.append("option down")
            elif p_up in ("SHIFT",):
                modifiers.append("shift down")
            else:
                main_key = p

        using_str = f" using {{{', '.join(modifiers)}}}" if modifiers else ""

        if main_key.upper() in cls.KEY_CODE_MAP:
            code = cls.KEY_CODE_MAP[main_key.upper()]
            cmd = f'tell application "System Events" to key code {code}{using_str}'
        else:
            k_char = main_key.lower() if len(main_key) == 1 else main_key
            cmd = f'tell application "System Events" to keystroke "{k_char}"{using_str}'

        try:
            subprocess.run(["osascript", "-e", cmd], timeout=2)
            return True
        except Exception as e:
            print(f"[HotkeyCommand] Erro ao enviar hotkey '{hotkey_str}': {e}")
            return False
