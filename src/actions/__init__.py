"""
Pacote de Ações Desacopladas (Command Pattern) para o Fifine AmpliGame D6.
"""

from .base import ActionCommand
from .registry import ActionRegistry
from . import app_action
from . import hotkey_action
from . import media_action
from . import system_action
from . import navigation_action
from . import device_action
from . import obs_action
from . import soundboard_action
from . import macro_action

__all__ = ["ActionCommand", "ActionRegistry"]
