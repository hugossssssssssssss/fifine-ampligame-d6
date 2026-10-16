/**
 * fifine Control Deck Studio Pro - Scene Menu Module
 * Gerencia o menu dropdown de contexto da cena (botão de 3 pontinhos ⋮).
 */

import { showToast, apiRenameProfile, apiDuplicateProfile, apiLinkApp } from './api.js';

export function bindProfileDropdownEvents(state, loadServerState, switchProfile, openLinkAppModal) {
  const btnMenu = document.getElementById('btnSceneMenu');
  const dropdown = document.getElementById('dropdownProfileMenu');
  const fileInputProfile = document.getElementById('fileInputProfile');

  if (btnMenu && dropdown) {
    btnMenu.onclick = (e) => {
      e.stopPropagation();
      const isVisible = dropdown.style.display === 'block';
      if (isVisible) {
        dropdown.style.display = 'none';
        return;
      }
      const rect = btnMenu.getBoundingClientRect();
      dropdown.style.top = `${rect.bottom + 6}px`;
      dropdown.style.left = `${Math.max(10, rect.right - 180)}px`;
      dropdown.style.zIndex = '9999';
      dropdown.style.display = 'block';
    };

    document.addEventListener('click', (e) => {
      if (!e.target.closest('#dropdownProfileMenu') && !e.target.closest('#btnSceneMenu')) {
        dropdown.style.display = 'none';
      }
    });

    // Renomear Perfil
    const itemRename = document.getElementById('menuItemRename');
    if (itemRename) {
      itemRename.onclick = async () => {
        dropdown.style.display = 'none';
        const currentName = state.profiles[state.activeProfile]?.name || state.activeProfile;
        const newName = prompt('Novo nome para a cena:', currentName);
        if (newName && newName.trim() && newName.trim() !== currentName) {
          const clean = newName.trim();
          showToast(`Renomeando cena para "${clean}"...`);
          try {
            const res = await apiRenameProfile(state.activeProfile, clean);
            if (res.success) {
              await loadServerState();
              showToast(`✓ Cena renomeada para "${clean}"`);
            }
          } catch (err) {
            showToast('Erro ao renomear cena');
          }
        }
      };
    }

    // Duplicar Perfil
    const itemDup = document.getElementById('menuItemDuplicate');
    if (itemDup) {
      itemDup.onclick = async () => {
        dropdown.style.display = 'none';
        showToast('Duplicando cena...');
        try {
          const data = await apiDuplicateProfile(state.activeProfile);
          if (data.success && data.new_id) {
            await loadServerState();
            switchProfile(data.new_id);
            showToast('✓ Cena duplicada com sucesso!');
          }
        } catch (err) {
          showToast('Erro ao duplicar cena');
        }
      };
    }

    // Vincular Aplicativo à Cena (App-Aware Auto-Switch)
    const itemLinkApp = document.getElementById('menuItemLinkApp');
    if (itemLinkApp) {
      itemLinkApp.onclick = () => {
        dropdown.style.display = 'none';
        if (openLinkAppModal) {
          openLinkAppModal(state.activeProfile);
        }
      };
    }

    // Exportar Perfil Atual
    const itemExport = document.getElementById('menuItemExport');
    if (itemExport) {
      itemExport.onclick = () => {
        dropdown.style.display = 'none';
        const profile = state.profiles[state.activeProfile];
        if (!profile) return;
        const blob = new Blob([JSON.stringify(profile, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${profile.name || state.activeProfile}.sdProfile.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('✓ Perfil exportado');
      };
    }

    // Importar Perfil
    const itemImport = document.getElementById('menuItemImport');
    if (itemImport && fileInputProfile) {
      itemImport.onclick = () => {
        dropdown.style.display = 'none';
        fileInputProfile.click();
      };

      fileInputProfile.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async (evt) => {
          try {
            const json = JSON.parse(evt.target.result);
            showToast('Importando perfil...');
            const res = await fetch('/api/profile/import', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ profile: json })
            });
            const data = await res.json();
            if (data.success) {
              await loadServerState();
              switchProfile(data.id);
              showToast('✓ Perfil importado com sucesso!');
            } else {
              showToast('Formato de perfil inválido.');
            }
          } catch (err) {
            showToast('Erro ao processar arquivo de perfil.');
          }
        };
        reader.readAsText(file);
      };
    }

    // Excluir Cena Atual
    const itemDelete = document.getElementById('menuItemDelete');
    if (itemDelete) {
      itemDelete.onclick = () => {
        dropdown.style.display = 'none';
        const btnDelScene = document.getElementById('btnDeleteScene');
        if (btnDelScene) btnDelScene.click();
      };
    }
  }
}
