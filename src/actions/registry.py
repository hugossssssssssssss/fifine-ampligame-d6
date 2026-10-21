"""
Registro e Despachante Central de Ações (Action Registry).
Implementa o Command Pattern, mapeando qualquer intenção para sua classe executora correspondente.
"""

from typing import Dict, Any, Optional, Union
from models.action import ActionModel
from .base import ActionCommand
from .app_action import OpenAppCommand, OpenUrlCommand
from .hotkey_action import HotkeyCommand
from .media_action import (
    VolumeUpCommand, VolumeDownCommand, MuteCommand,
    PlayPauseCommand, NextTrackCommand, PrevTrackCommand, StopMusicCommand
)
from .system_action import (
    CloseWindowCommand, CloseAppCommand, MinimizeWindowCommand,
    FullscreenToggleCommand, LockScreenCommand, ShowDesktopCommand,
    LaunchpadCommand, MissionControlCommand, SiriCommand, ScreenshotCommand,
    EmoticonsCommand, TextInputCommand, ShellCommand, MouseEventCommand,
    SystemStatsCommand, ForceQuitCommand, EmptyTrashCommand, SleepMacCommand
)
from .navigation_action import NavigationCommand
from .device_action import BrightnessCommand, SleepDeviceCommand, ToggleStateCommand
from .obs_action import OBSActionCommand
from .soundboard_action import SoundboardPlayCommand, SoundboardStopCommand
from .macro_action import MacroCommand


class ActionRegistry:
    """Mapeia identificadores de ações e executa comandos de forma desacoplada."""

    _commands: Dict[str, ActionCommand] = {}

    @classmethod
    def initialize(cls):
        """Registra instâncias de comandos suportados."""
        app_cmd = OpenAppCommand()
        url_cmd = OpenUrlCommand()
        hotkey_cmd = HotkeyCommand()
        text_cmd = TextInputCommand()
        shell_cmd = ShellCommand()
        toggle_cmd = ToggleStateCommand()
        nav_cmd = NavigationCommand()
        obs_cmd = OBSActionCommand()
        macro_cmd = MacroCommand()
        mouse_cmd = MouseEventCommand()

        cls._commands = {
            # Aplicativos e URLs
            "open": app_cmd,
            "open_app": app_cmd,
            "open_path": app_cmd,
            "openapps": app_cmd,
            "system.open": app_cmd,
            "system.openapps": app_cmd,
            "website": url_cmd,
            "open_url": url_cmd,
            "url": url_cmd,
            "system.website": url_cmd,

            # Atalhos e Texto
            "hotkey": hotkey_cmd,
            "system.hotkey": hotkey_cmd,
            "text": text_cmd,
            "password": text_cmd,
            "system.text": text_cmd,
            "system.password": text_cmd,
            "shell": shell_cmd,
            "shell_command": shell_cmd,
            "terminal": shell_cmd,
            "system.shell": shell_cmd,

            # Alternância de Estado
            "toggle": toggle_cmd,
            "hotkeyswitch": toggle_cmd,
            "system.toggle": toggle_cmd,

            # Multimídia
            "volumeup": VolumeUpCommand(),
            "volumedown": VolumeDownCommand(),
            "mute": MuteCommand(),
            "play": PlayPauseCommand(),
            "playpause": PlayPauseCommand(),
            "multimedia_play": PlayPauseCommand(),
            "next": NextTrackCommand(),
            "multimedia_next": NextTrackCommand(),
            "prev": PrevTrackCommand(),
            "multimedia_prev": NextTrackCommand(),
            "stop": StopMusicCommand(),

            # Controles de Janelas & Mac
            "close_window": CloseWindowCommand(),
            "window_close": CloseWindowCommand(),
            "close_app": CloseAppCommand(),
            "app_close": CloseAppCommand(),
            "minimize_window": MinimizeWindowCommand(),
            "window_minimize": MinimizeWindowCommand(),
            "fullscreen_toggle": FullscreenToggleCommand(),
            "window_fullscreen": FullscreenToggleCommand(),
            "lock_screen": LockScreenCommand(),
            "screenlock": LockScreenCommand(),
            "show_desktop": ShowDesktopCommand(),
            "displaydesktop": ShowDesktopCommand(),
            "launchpad": LaunchpadCommand(),
            "mission": MissionControlCommand(),
            "dispatchcenter": MissionControlCommand(),
            "siri": SiriCommand(),
            "screenshot": ScreenshotCommand(),
            "emoticons": EmoticonsCommand(),
            "system_stats": SystemStatsCommand(),
            "systemstats": SystemStatsCommand(),
            "force_quit": ForceQuitCommand(),
            "forcequit": ForceQuitCommand(),
            "empty_trash": EmptyTrashCommand(),
            "emptytrash": EmptyTrashCommand(),
            "sleep_mac": SleepMacCommand(),
            "mac_sleep": SleepMacCommand(),

            # Quicktools Oficiais Fifine
            "quicktool.calculator": app_cmd,
            "calculator": app_cmd,
            "quicktool.mail": app_cmd,
            "mail": app_cmd,
            "quicktool.music": app_cmd,
            "music": app_cmd,
            "quicktool.taskmanager": app_cmd,
            "taskmanager": app_cmd,

            # Navegação
            "page": nav_cmd,
            "change_page": nav_cmd,
            "rotate": nav_cmd,
            "openchild": nav_cmd,
            "backtoparent": nav_cmd,
            "folder": nav_cmd,
            "page.goto": nav_cmd,
            "page.previous": nav_cmd,
            "page.next": nav_cmd,
            "page.indicator": nav_cmd,

            # Hardware & Utilitários
            "brightness": BrightnessCommand(),
            "devsleep": SleepDeviceCommand(),
            "sleep": SleepDeviceCommand(),
            "mouse": mouse_cmd,
            "mouse.event": mouse_cmd,
            "password": text_cmd,

            # Soundboard
            "soundboard": SoundboardPlayCommand(),
            "playaudio": SoundboardPlayCommand(),
            "audioplay": SoundboardPlayCommand(),
            "stopaudioplay": SoundboardStopCommand(),
            "stop_audio": SoundboardStopCommand(),
            "stopaudio": SoundboardStopCommand(),

            # OBS & Macros
            "obs": obs_cmd,
            "obsstudio": obs_cmd,
            "multiaction": macro_cmd,
            "routine": macro_cmd,
            "macro": macro_cmd,
        }

    @classmethod
    def resolve(cls, action_type_or_uuid: str) -> Optional[ActionCommand]:
        """Localiza o comando adequado por correspondência direta ou por palavra-chave."""
        if not cls._commands:
            cls.initialize()

        key = (action_type_or_uuid or "").lower().strip()

        # 1. Correspondência exata no dicionário
        if key in cls._commands:
            return cls._commands[key]

        # 2. Resoluções por palavras-chave com ordem estrita de precedência

        # A) OBS & Macros
        if any(k in key for k in ("multiaction", "routine", "macro")):
            return cls._commands["multiaction"]
        if any(k in key for k in ("obsstudio", "obs_", "obs.")):
            return cls._commands["obs"]

        # B) Soundboard: parar áudio DEVE ser testado ANTES de playaudio (stopaudioplay contém soundboard)
        if any(k in key for k in ("stopaudioplay", "stop_audio", "stopaudio")):
            return cls._commands["stopaudioplay"]
        if any(k in key for k in ("soundboard", "playaudio", "audioplay")):
            return cls._commands["playaudio"]

        # C) Navegação de Páginas e Pastas: DEVE vir ANTES de mídias (page.previous e page.next contêm prev e next)
        if any(k in key for k in ("openchild", "backtoparent", "rotate", "folder")) or (
            ("page." in key or "page_" in key) and any(p in key for p in ("prev", "next", "goto", "indicator", "previous"))
        ):
            return cls._commands["page"]

        # D) Abrir Apps e URLs
        if any(k in key for k in ("open", "openapps", "open_app")):
            return cls._commands["open"]
        if any(k in key for k in ("website", "url")):
            return cls._commands["website"]

        # E) Entrada de Texto, Teclado e Senha
        if any(k in key for k in ("hotkey", "hotkeyswitch")):
            return cls._commands["hotkey"]
        if "password" in key:
            return cls._commands["password"]
        if "text" in key:
            return cls._commands["text"]
        if "shell" in key:
            return cls._commands["shell"]

        # F) Teclas de Mídia (volumeup, volumedown, mute, play, next, prev)
        if any(k in key for k in ("volumeup", "volumedown", "mute", "play", "next", "prev")):
            for k in ("volumeup", "volumedown", "mute", "play", "next", "prev"):
                if k in key:
                    return cls._commands[k]

        # G) Janelas e Sistema macOS
        if "close" in key and "window" in key:
            return cls._commands["close_window"]
        if "close" in key:
            return cls._commands["close_app"]
        if "minimize" in key:
            return cls._commands["minimize_window"]
        if "fullscreen" in key:
            return cls._commands["fullscreen_toggle"]
        if "lock" in key:
            return cls._commands["lock_screen"]
        if "desktop" in key:
            return cls._commands["show_desktop"]
        if "screenshot" in key:
            return cls._commands["screenshot"]
        if "siri" in key:
            return cls._commands["siri"]
        if any(k in key for k in ("dispatchcenter", "dispatch", "mission")):
            return cls._commands["dispatchcenter"]
        if "launchpad" in key:
            return cls._commands["launchpad"]

        # H) Hardware e Mouse
        if "brightness" in key:
            return cls._commands["brightness"]
        if any(k in key for k in ("devsleep", "sleep")):
            return cls._commands["devsleep"]
        if any(k in key for k in ("mouse.event", "mouse")):
            return cls._commands["mouse.event"]
        if "toggle" in key:
            return cls._commands["toggle"]

        return None

    @classmethod
    def dispatch(cls, action_input: Union[ActionModel, Dict[str, Any]], slot: Optional[int] = None, engine: Any = None) -> bool:
        """Ponto de entrada unificado para execução de qualquer ação no sistema."""
        if isinstance(action_input, dict):
            action = ActionModel.from_dict(action_input)
        elif isinstance(action_input, ActionModel):
            action = action_input
        else:
            return False

        if not action:
            return False

        # Identifica tipo de busca pelo UUID ou pelo tipo
        lookup_key = action.uuid or action.type
        command = cls.resolve(lookup_key)

        if not command and action.type != lookup_key:
            command = cls.resolve(action.type)

        # Fallback inteligente se a ação tiver campos óbvios
        if not command:
            if action.path or action.target:
                command = cls._commands.get("open")
            elif action.keys:
                command = cls._commands.get("hotkey")
            elif action.url:
                command = cls._commands.get("website")
            elif action.command:
                command = cls._commands.get("shell")
            elif action.text:
                command = cls._commands.get("text")

        if command:
            # Quicktools especiais com targets padronizados
            act_lower = (action.uuid or action.type).lower()
            if "calculator" in act_lower:
                action.target = "Calculator"
            elif "mail" in act_lower:
                action.target = "Mail"
            elif "music" in act_lower:
                action.target = "Music"
            elif "taskmanager" in act_lower:
                action.target = "Activity Monitor"
            elif "browser.back" in act_lower:
                return HotkeyCommand.send_hotkey("Cmd + [")
            elif "browser.forward" in act_lower:
                return HotkeyCommand.send_hotkey("Cmd + ]")
            elif "browser.refresh" in act_lower:
                return HotkeyCommand.send_hotkey("Cmd + R")
            elif "browser.collect" in act_lower:
                return HotkeyCommand.send_hotkey("Cmd + D")

            return command.execute(action, slot=slot, engine=engine)

        print(f"[ActionRegistry] Nenhuma ação registrada para: '{lookup_key}' (tipo: '{action.type}')")
        return False


# Auto-inicializa o registro de comandos na carga do módulo
ActionRegistry.initialize()
