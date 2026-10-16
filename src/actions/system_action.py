"""
Comandos de Janelas, Utilitários de Sistema e Ferramentas macOS.
Controla fechamento de janelas, lock screen, launchpad, mission control, digitação e shell.
"""

import time
import subprocess
from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel


class CloseWindowCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "w" using command down'], timeout=2)
        return True


class CloseAppCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "q" using command down'], timeout=2)
        return True


class MinimizeWindowCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "m" using command down'], timeout=2)
        return True


class FullscreenToggleCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "f" using {command down, control down}'], timeout=2)
        return True


class LockScreenCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "q" using {command down, control down}'], timeout=2)
        return True


class ShowDesktopCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 103'], timeout=2)
        return True


class LaunchpadCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.Popen(["open", "-a", "Launchpad"])
        return True


class MissionControlCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.Popen(["open", "-a", "Mission Control"])
        return True


class SiriCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.Popen(["open", "-a", "Siri"])
        return True


class ScreenshotCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.Popen(["screencapture", "-i", "-c"])
        return True


class EmoticonsCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke " " using {command down, control down}'], timeout=2)
        return True


class TextInputCommand(ActionCommand):
    """Digitação de texto ou senha via clipboard ou digitação simulada."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        txt = action.text
        if not txt:
            return False

        if action.clipboard:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(txt.encode("utf-8"))
            time.sleep(0.05)
            subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'], timeout=2)
        else:
            escaped = txt.replace('\\', '\\\\').replace('"', '\\"')
            subprocess.run(["osascript", "-e", f'tell application "System Events" to keystroke "{escaped}"'], timeout=2)

        if action.enter:
            time.sleep(0.05)
            subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 36'], timeout=2)

        return True


class ShellCommand(ActionCommand):
    """Execução assíncrona de comandos de terminal."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        cmd = action.command or action.target or ""
        if cmd:
            print(f"[ShellCommand] Executando comando em background: {cmd}")
            subprocess.Popen(cmd, shell=True, executable="/bin/zsh")
            return True
        return False
