"""
Comando para Abertura Inteligente de Aplicativos e Arquivos no macOS.
Suporta caminhos absolutos, nomes de aplicativos, aliases e descompactação conceitual (.zip).
"""

import os
import subprocess
from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel


class OpenAppCommand(ActionCommand):
    """Abre aplicativos, arquivos ou pastas no macOS com resolução inteligente."""

    APP_SEARCH_DIRS = [
        "/Applications",
        "/System/Applications",
        "/System/Applications/Utilities",
        os.path.expanduser("~/Applications"),
        os.path.expanduser("~/Downloads"),
        "/Applications/Utilities",
    ]

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        target = action.target or action.path or ""
        return self.open_target(target)

    @classmethod
    def open_target(cls, target: str) -> bool:
        target = str(target or "").strip()
        if not target:
            return False

        # 1. Extrai nome base do app (eliminando diretórios antigos e extensões .zip/.app)
        raw_name = os.path.basename(target)
        clean_name = raw_name[:-4] if raw_name.lower().endswith(".zip") else raw_name
        clean_name = clean_name[:-4] if clean_name.lower().endswith(".app") else clean_name

        # 2. Tenta ativação nativa via AppleScript (método mais rápido e confiável no macOS)
        if clean_name and not target.startswith("http://") and not target.startswith("https://"):
            try:
                scpt = f'tell application "{clean_name}" to activate'
                r = subprocess.run(["osascript", "-e", scpt], capture_output=True, text=True, timeout=3)
                if r.returncode == 0:
                    print(f"[OpenAppCommand] Aplicativo '{clean_name}' ativado com sucesso via AppleScript")
                    return True
            except Exception as e:
                print(f"[OpenAppCommand] AppleScript aviso: {e}")

        # 3. Caminho existente diretamente no sistema de arquivos
        expanded = os.path.expanduser(target)
        if os.path.exists(expanded) and not expanded.endswith(".zip"):
            print(f"[OpenAppCommand] Abrindo caminho existente: '{expanded}'")
            subprocess.Popen(["/usr/bin/open", expanded])
            return True

        # 4. Busca nas pastas padrão do macOS pelo nome limpo
        for app_dir in cls.APP_SEARCH_DIRS:
            if not os.path.exists(app_dir):
                continue
            cand = os.path.join(app_dir, f"{clean_name}.app")
            if os.path.exists(cand):
                print(f"[OpenAppCommand] Encontrado aplicativo em '{cand}' -> Abrindo")
                subprocess.Popen(["/usr/bin/open", cand])
                return True

        # 5. Tenta 'open -a' pelo nome limpo do app (ex: 'open -a Safari', 'open -a ResetCamera')
        if clean_name:
            print(f"[OpenAppCommand] Tentando 'open -a \"{clean_name}\"'...")
            r = subprocess.run(["/usr/bin/open", "-a", clean_name], capture_output=True, text=True)
            if r.returncode == 0:
                print(f"[OpenAppCommand] Sucesso ao abrir '{clean_name}' via 'open -a'")
                return True

        # 6. Tenta 'open -a' com o target original
        r = subprocess.run(["/usr/bin/open", "-a", target], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"[OpenAppCommand] Sucesso ao abrir '{target}' via 'open -a'")
            return True

        # 7. Fallback final genérico 'open' (para URLs ou arquivos padrão)
        print(f"[OpenAppCommand] Fallback genérico 'open \"{target}\"'...")
        subprocess.Popen(["/usr/bin/open", target])
        return True


class OpenUrlCommand(ActionCommand):
    """Abre URLs e websites no navegador padrão do macOS."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        url = action.url or action.target or action.path or ""
        if not url:
            return False

        if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("file://"):
            url = "https://" + url

        print(f"[OpenUrlCommand] Abrindo URL no navegador: {url}")
        subprocess.Popen(["open", url])
        return True
