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

        # 1. Normaliza caminhos que tenham .app.zip (artefato comum do HotSpot)
        clean_target = target
        if clean_target.lower().endswith(".app.zip"):
            clean_target = clean_target[:-4]

        # 2. Caminho existente diretamente no sistema de arquivos
        expanded = os.path.expanduser(clean_target)
        if os.path.exists(expanded):
            print(f"[OpenAppCommand] Abrindo caminho direto no macOS: '{expanded}'")
            subprocess.Popen(["/usr/bin/open", expanded])
            return True

        # 3. Extrai nome base do app (eliminando diretórios antigos e extensões .zip/.app)
        raw_name = os.path.basename(target)
        clean_name = raw_name[:-4] if raw_name.lower().endswith(".zip") else raw_name
        clean_name = clean_name[:-4] if clean_name.lower().endswith(".app") else clean_name

        # Mapeamento de nomes localizados (Português <-> Inglês) para apps nativos do macOS
        name_aliases = {
            "calendar": ["Calendar", "Calendário"],
            "calendário": ["Calendar", "Calendário"],
            "system settings": ["System Settings", "Ajustes do Sistema", "System Preferences", "Preferências do Sistema"],
            "ajustes do sistema": ["System Settings", "Ajustes do Sistema", "System Preferences"],
            "preferências do sistema": ["System Preferences", "System Settings", "Ajustes do Sistema"],
            "calculator": ["Calculator", "Calculadora"],
            "calculadora": ["Calculator", "Calculadora"],
            "music": ["Music", "Música"],
            "música": ["Music", "Música"],
            "safari": ["Safari"],
            "notes": ["Notes", "Notas"],
            "notas": ["Notes", "Notas"],
            "reminders": ["Reminders", "Lembretes"],
            "lembretes": ["Reminders", "Lembretes"],
            "mail": ["Mail"],
            "terminal": ["Terminal"],
            "activity monitor": ["Activity Monitor", "Monitor de Atividade"],
            "monitor de atividade": ["Activity Monitor", "Monitor de Atividade"],
        }

        candidates_to_try = [clean_name]
        lower_clean = clean_name.lower()
        if lower_clean in name_aliases:
            candidates_to_try.extend(name_aliases[lower_clean])

        # 4. Tenta 'open -a <nome>' para cada candidato
        for cand in candidates_to_try:
            if not cand:
                continue
            r = subprocess.run(["/usr/bin/open", "-a", cand], capture_output=True, text=True)
            if r.returncode == 0:
                print(f"[OpenAppCommand] Sucesso ao abrir '{cand}' via 'open -a'")
                return True

        # 5. Busca nas pastas padrão do macOS pelo nome limpo
        for app_dir in cls.APP_SEARCH_DIRS:
            if not os.path.exists(app_dir):
                continue
            for cand in candidates_to_try:
                cand_path = os.path.join(app_dir, f"{cand}.app")
                if os.path.exists(cand_path):
                    print(f"[OpenAppCommand] Encontrado aplicativo em '{cand_path}' -> Abrindo")
                    subprocess.Popen(["/usr/bin/open", cand_path])
                    return True

        # 6. Fallback AppleScript
        for cand in candidates_to_try:
            try:
                scpt = f'tell application "{cand}" to activate'
                r = subprocess.run(["osascript", "-e", scpt], capture_output=True, text=True, timeout=2)
                if r.returncode == 0:
                    print(f"[OpenAppCommand] Aplicativo '{cand}' ativado com sucesso via AppleScript")
                    return True
            except Exception:
                pass

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
