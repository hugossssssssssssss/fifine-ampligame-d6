#!/usr/bin/env python3
"""
Fifine Guardian - Proteção Atômica contra Resets do fifine Control Deck.app
Monitora os perfis oficiais e impede que o aplicativo corrompa ou resete o manifest.json.
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path

HOME = Path.home()
STREAMDOCK_DIR = HOME / "Library" / "Application Support" / "HotSpot" / "StreamDock"
PROFILES_DIR = STREAMDOCK_DIR / "profiles"
BACKUP_DIR = STREAMDOCK_DIR / "profiles_golden_backup"

def ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def sync_profiles():
    if not PROFILES_DIR.exists():
        return

    for profile_folder in PROFILES_DIR.glob("*.sdProfile"):
        manifest_file = profile_folder / "manifest.json"
        backup_folder = BACKUP_DIR / profile_folder.name
        backup_manifest = backup_folder / "manifest.json"
        backup_images = backup_folder / "Images"
        profile_images = profile_folder / "Images"

        if not manifest_file.exists():
            continue

        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Arquivo manifest.json vazio!")
                data = json.loads(content)
                actions = data.get("Actions", {})
        except Exception as e:
            # Arquivo corrompido ou inacessível: restaurar do backup
            if backup_manifest.exists():
                print(f"[GUARDIAN] ALERTA: Corrupção detectada em {profile_folder.name} ({e})! Restaurando...")
                shutil.copyfile(backup_manifest, manifest_file)
            continue

        # Se as ações foram esvaziadas (bug de reset da Fifine)
        if len(actions) == 0 and backup_manifest.exists():
            try:
                with open(backup_manifest, "r", encoding="utf-8") as bf:
                    b_data = json.load(bf)
                    b_actions = b_data.get("Actions", {})
                    if len(b_actions) > 0:
                        print(f"[GUARDIAN] ALERTA: Tentativa de reset detectada em {profile_folder.name}! Restaurando {len(b_actions)} teclas...")
                        shutil.copyfile(backup_manifest, manifest_file)
                        continue
            except Exception:
                pass

        # Se o manifest está saudável com ações configuradas, atualiza o backup
        if len(actions) > 0:
            backup_folder.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(manifest_file, backup_manifest)
            if profile_images.exists():
                backup_images.mkdir(parents=True, exist_ok=True)
                for img in profile_images.glob("*.*"):
                    b_img = backup_images / img.name
                    if not b_img.exists() or b_img.stat().st_size != img.stat().st_size:
                        shutil.copyfile(img, b_img)

def run_loop():
    print("[GUARDIAN] Fifine Guardian Ativo - Blindagem de Perfis Ativada.")
    print(f"[GUARDIAN] Monitorando: {PROFILES_DIR}")
    print(f"[GUARDIAN] Protegido em: {BACKUP_DIR}")
    ensure_backup_dir()
    while True:
        try:
            sync_profiles()
        except Exception as e:
            pass
        time.sleep(1.0)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        print("[GUARDIAN] Restaurando todos os perfis do backup dourado...")
        ensure_backup_dir()
        for b_folder in BACKUP_DIR.glob("*.sdProfile"):
            dest_folder = PROFILES_DIR / b_folder.name
            dest_folder.mkdir(parents=True, exist_ok=True)
            b_manifest = b_folder / "manifest.json"
            if b_manifest.exists():
                shutil.copyfile(b_manifest, dest_folder / "manifest.json")
            b_images = b_folder / "Images"
            if b_images.exists():
                d_images = dest_folder / "Images"
                d_images.mkdir(parents=True, exist_ok=True)
                for img in b_images.glob("*.*"):
                    shutil.copyfile(img, d_images / img.name)
        print("[GUARDIAN] Restauração concluída com sucesso.")
    else:
        run_loop()
