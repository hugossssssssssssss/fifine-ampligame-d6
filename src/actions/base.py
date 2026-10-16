"""
Interface Base para o Command Pattern de Ações do Fifine AmpliGame D6.
Cada comportamento do computador é encapsulado em uma classe com responsabilidade única.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from models.action import ActionModel


class ActionCommand(ABC):
    """Classe base abstrata para todos os comandos executáveis do StreamDeck."""

    @abstractmethod
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        """
        Executa a ação correspondente no macOS ou hardware.
        Retorna True em caso de sucesso.
        """
        pass
