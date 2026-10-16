"""
Gerenciador de Armazenamento Atômico do Fifine AmpliGame D6.
Garante persistência à prova de falhas com escrita atômica (tempfile + os.replace).
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Optional
from .config import ConfigModel


class StorageManager:
    """Gerencia a leitura e escrita atômica de configurações no disco."""

    @staticmethod
    def load(filepath: Path) -> ConfigModel:
        """Carrega a configuração a partir do arquivo JSON com tratamento de erros."""
        if not filepath.exists():
            return ConfigModel.from_dict({})

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ConfigModel.from_dict(data)
        except Exception as e:
            print(f"[StorageManager] Erro ao carregar {filepath}: {e}")
            # Se o arquivo estiver corrompido, tenta carregar backup .bak se existir
            bak_path = filepath.with_suffix(".json.bak")
            if bak_path.exists():
                try:
                    print(f"[StorageManager] Restaurando do backup {bak_path}...")
                    with open(bak_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return ConfigModel.from_dict(data)
                except Exception as bak_err:
                    print(f"[StorageManager] Erro ao restaurar backup: {bak_err}")

            return ConfigModel.from_dict({})

    @staticmethod
    def save_atomic(config, filepath: Path) -> bool:
        """Salva a configuração atomicamente usando arquivo temporário no mesmo diretório."""
        parent_dir = filepath.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        if hasattr(config, "to_dict"):
            data = config.to_dict()
        elif isinstance(config, dict):
            data = config
        else:
            data = {}
        data_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

        # Cria arquivo temporário no mesmo sistema de arquivos para permitir os.replace atômico
        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(prefix="d6_cfg_", suffix=".tmp", dir=str(parent_dir))
            with os.fdopen(fd, "wb") as f:
                f.write(data_bytes)
                f.flush()
                os.fsync(f.fileno())  # Garante gravação física no disco

            fd = None  # Fechado pelo os.fdopen

            # Cria cópia de segurança antes de substituir se o original existir
            if filepath.exists():
                try:
                    import shutil
                    shutil.copy2(filepath, filepath.with_suffix(".json.bak"))
                except Exception:
                    pass

            # Substituição atômica garantida pelo sistema operacional POSIX
            os.replace(tmp_path, filepath)
            return True
        except Exception as e:
            print(f"[StorageManager] Erro ao salvar atômico {filepath}: {e}")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            return False
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass
