/**
 * fifine Control Deck Studio Pro (1:1 Logic Engine)
 * Sincronização interativa, drag-and-drop, Property Inspector dinâmico e gestão de perfis.
 */

import { initTheme } from './modules/theme.js';
import { bindProfileDropdownEvents as setupProfileDropdown } from './modules/sceneMenu.js';

// Estado Global da Aplicação
const state = {
  activeProfile: 'nitro', // 'principal' ou 'nitro'
  selectedSlot: 0, // 0 a 14
  clipboard: null, // Área de transferência para Copiar / Colar teclas (⌘C / ⌘V)
  profiles: {
    principal: {
      id: 'principal',
      name: 'Cena Padrão',
      keys: {
        0: {
          title: 'RESETAR\nCAMERA',
          bg: '#18181b',
          textColor: '#ffffff',
          category: 'Caixa de Ferramentas',
          actionType: 'open',
          actionName: 'Abra uma aplicação',
          path: '/Users/hugosilva/Downloads/ResetCamera.app',
          icon: ''
        },
        1: {
          title: 'ABRE',
          bg: '#18181b',
          textColor: '#ffffff',
          category: 'Caixa de Ferramentas',
          actionType: 'open',
          actionName: 'Abre',
          icon: ''
        }
      }
    },
    nitro: {
      id: 'nitro',
      name: 'Nitro',
      keys: {
        0: {
          title: '',
          bg: '#004481',
          textColor: '#ffffff',
          category: 'Caixa de Ferramentas',
          actionType: 'text',
          actionName: 'Texto',
          textPayload: '',
          pressEnter: false,
          useClipboard: true,
          icon: ''
        },
        1: {
          title: '',
          bg: '#008855',
          textColor: '#ffffff',
          category: 'Caixa de Ferramentas',
          actionType: 'text',
          actionName: 'Texto',
          textPayload: '',
          pressEnter: false,
          useClipboard: true,
          icon: ''
        },
        5: {
          title: '',
          bg: '#0066aa',
          textColor: '#ffffff',
          category: 'Caixa de Ferramentas',
          actionType: 'text',
          actionName: 'Texto',
          textPayload: '',
          pressEnter: false,
          useClipboard: true,
          icon: ''
        },
        6: {
          title: '',
          bg: '#88b010',
          textColor: '#ffffff',
          category: 'Caixa de Ferramentas',
          actionType: 'text',
          actionName: 'Texto',
          textPayload: '',
          pressEnter: false,
          useClipboard: true,
          icon: ''
        },
        8: {
          title: '',
          bg: '#e65c00',
          textColor: '#ffffff',
          category: 'Caixa de Ferramentas',
          actionType: 'text',
          actionName: 'Texto',
          textPayload: '',
          pressEnter: false,
          useClipboard: true,
          icon: ''
        },
        10: {
          title: '',
          bg: '#3cb4b4',
          textColor: '#ffffff',
          category: 'Caixa de Ferramentas',
          actionType: 'text',
          actionName: 'Texto',
          textPayload: '',
          pressEnter: false,
          useClipboard: true,
          icon: ''
        },
        11: {
          title: '',
          bg: '#99d6d6',
          textColor: '#ffffff',
          category: 'Caixa de Ferramentas',
          actionType: 'text',
          actionName: 'Texto',
          textPayload: '',
          pressEnter: false,
          useClipboard: true,
          icon: ''
        }
      }
    }
  }
};

// Carregamento dinâmico de estado do servidor
async function loadServerState(isBackground = false) {
  try {
    const res = await fetch('/api/state?_t=' + Date.now());
    if (res.ok) {
      const data = await res.json();
      if (data.pages) {
        // Reconstrói state.profiles com dados frescos do servidor
        const newProfiles = {};
        Object.keys(data.pages).forEach(pageId => {
          const pg = data.pages[pageId];
          newProfiles[pageId] = {
            id: pageId,
            name: pg.name || pageId,
            isFolder: !!pg.is_folder,
            parentPage: pg.parent_page || '',
            parentSlot: pg.parent_slot !== undefined ? pg.parent_slot : null,
            nativeFolder: pg.native_folder || '',
            linked_app: pg.linked_app || '',
            keys: {}
          };

          if (pg.keys) {
            Object.keys(pg.keys).forEach(kNum => {
              const kData = pg.keys[kNum];
              const slotIdx = parseInt(kNum) - 1;
              if (slotIdx >= 0 && slotIdx < 15) {
                const actType = (kData.action?.type || '').toLowerCase();
                const actUuid = (kData.action?.uuid || '').toLowerCase();
                let uiActionType = actType || 'action';
                if (actType === 'openchild' || actUuid.includes('openchild') || actType === 'folder') {
                  uiActionType = 'folder';
                } else if (actType === 'backtoparent' || actUuid.includes('backtoparent')) {
                  uiActionType = 'backtoparent';
                } else if (actType === 'multiaction' || actType === 'routine' || actUuid.includes('routine')) {
                  uiActionType = 'multiaction';
                } else if (actType === 'obs' || actUuid.includes('obsstudio')) {
                  uiActionType = 'obs';
                }

                newProfiles[pageId].keys[slotIdx] = {
                  title: kData.title || '',
                  subtitle: kData.subtitle || '',
                  bg: kData.bg || '#18181b',
                  textColor: kData.textColor || '#ffffff',
                  fontSize: (kData.fontSize || 12) + 'px',
                  actionType: uiActionType,
                  actionUuid: kData.action?.uuid || '',
                  target: kData.action?.target || '',
                  folderId: kData.action?.target || '',
                  actionName: kData.title || 'Ação',
                  path: kData.action?.target || '',
                  textPayload: kData.action?.text || '',
                  pressEnter: !!kData.action?.enter,
                  imagePath: kData.imagePath || '',
                  icon: kData.icon || '',
                  steps: Array.isArray(kData.action?.steps) ? kData.action.steps : []
                };
              }
            });
          }
        });
        // Se estiver em background, preserva a tecla que o usuário está ativamente editando no momento
        if (isBackground && state.selectedSlot !== null && state.selectedSlot !== undefined) {
          const curEditingKey = state.profiles[state.activeProfile]?.keys?.[state.selectedSlot];
          if (curEditingKey && newProfiles[state.activeProfile]) {
            if (!newProfiles[state.activeProfile].keys) {
              newProfiles[state.activeProfile].keys = {};
            }
            newProfiles[state.activeProfile].keys[state.selectedSlot] = {
              ...newProfiles[state.activeProfile].keys[state.selectedSlot],
              ...curEditingKey
            };
          }
        }

        state.profiles = newProfiles;
      }

      if (data.auto_switch_enabled !== undefined) {
        state.autoSwitchEnabled = !!data.auto_switch_enabled;
      }
      if (data.frontmost_app) {
        state.frontmostApp = data.frontmost_app;
      }
      if (data.led_sleep_follow !== undefined) {
        state.ledSleepFollow = !!data.led_sleep_follow;
        const chkLed = document.getElementById('settingLedSleepFollowCheck');
        if (chkLed) {
          chkLed.checked = state.ledSleepFollow;
        }
      }
      if (data.screen_off_seconds !== undefined) {
        state.screenOffSeconds = data.screen_off_seconds;
        const selScreenOff = document.getElementById('settingScreenOffSelect');
        if (selScreenOff) {
          selScreenOff.value = String(data.screen_off_seconds);
        }
      }
      if (data.is_asleep !== undefined) {
        state.isAsleep = !!data.is_asleep;
        const statusText = document.querySelector('.status-text');
        const statusDot = document.querySelector('.status-dot');
        const btnNavSleep = document.getElementById('btnNavSleep');
        if (state.isAsleep) {
          if (statusText) statusText.textContent = 'Em Repouso (Sleep)';
          if (statusDot) statusDot.style.background = '#f59e0b';
          if (btnNavSleep) btnNavSleep.classList.add('active');
        } else {
          if (statusText) statusText.textContent = 'Conectado';
          if (statusDot) statusDot.style.background = '#22c55e';
          if (btnNavSleep) btnNavSleep.classList.remove('active');
        }
      }

      const isUserTyping = document.activeElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);
      const pageChanged = (data.active_page && state.profiles[data.active_page] && state.activeProfile !== data.active_page);

      if (!isBackground) {
        if (data.active_page && state.profiles[data.active_page]) {
          state.activeProfile = data.active_page;
        } else if (!state.profiles[state.activeProfile]) {
          state.activeProfile = Object.keys(state.profiles)[0] || 'principal';
        }
        renderSceneList();
        renderDeckGrid();
        updateSceneInspector();
        selectKey(state.selectedSlot || 0);
      } else if (pageChanged && !isUserTyping) {
        state.activeProfile = data.active_page;
        renderSceneList();
        renderDeckGrid();
        updateSceneInspector();
      }
    }
  } catch (e) {
    if (!isBackground) {
      console.warn('API /api/state não acessível no momento:', e);
      renderSceneList();
      renderDeckGrid();
      updateSceneInspector();
      selectKey(state.selectedSlot || 0);
    }
  }
}

// Inicialização com render imediato e sincronização com o hardware
document.addEventListener('DOMContentLoaded', async () => {
  // Inicializa gerenciador de temas (Dark / Light / Auto)
  initThemeManager();

  // Render imediato para exibição instantânea de cenas e teclas sem aguardar rede
  renderSceneList();
  renderDeckGrid();
  selectKey(state.selectedSlot || 0);

  // Carrega estado fresco do servidor/hardware
  await loadServerState();
  bindEvents();
  initObsSettings();
  initWallpaperMuralModal();
  initModals();

  // Polling a cada 3.5 segundos para refletir novas cenas criadas fora da janela e telemetria OBS
  setInterval(() => {
    loadServerState(true);
    const ctxObs = document.getElementById('fieldsContextObs');
    if (ctxObs && ctxObs.style.display !== 'none') {
      const curKey = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (curKey) updateObsContextPanel(curKey);
    }
  }, 3500);

  // Monitor em tempo real de cliques no hardware físico (sincroniza a animação tátil de afundamento na tela)
  let lastPhysicalPressTs = 0;
  setInterval(async () => {
    try {
      const res = await fetch(`/api/press_events?since=${lastPhysicalPressTs}&_t=${Date.now()}`);
      if (res.ok) {
        const ev = await res.json();
        if (ev.has_new && ev.slot !== null && ev.slot !== undefined) {
          lastPhysicalPressTs = ev.ts;
          const slotNum = parseInt(ev.slot, 10);
          // O hardware envia 1-indexed (1 a 15); a UI do studio usa 0-indexed (0 a 14)
          const uiSlot = slotNum >= 1 && slotNum <= 15 ? slotNum - 1 : slotNum;
          triggerKeyAnimation(uiSlot);
        }
      }
    } catch (_) {}
  }, 120);
});

// Alterna as abas laterais direitas (Propriedades, Ações, Loja, Skins, Ajustes)
function switchRightTab(tabId) {
  const tabs = document.querySelectorAll('.side-tab-btn');
  const panes = document.querySelectorAll('.tab-pane');
  
  tabs.forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  
  panes.forEach(pane => {
    pane.classList.toggle('active', pane.id === tabId);
  });

  if (tabId === 'tabPaneStore') {
    loadStoreIconPacks();
  } else if (tabId === 'tabPaneSkins') {
    loadLayoutSkins();
  } else if (tabId === 'tabPaneSettings') {
    fetchObsStatus();
  }
}

// Renderiza a lista de Cenas / Perfis com suporte a arrastar teclas e badge de App vinculado
function renderSceneList() {
  const container = document.getElementById('sceneList');
  if (!container) return;
  container.innerHTML = '';

  const activeProf = state.profiles[state.activeProfile];
  const hdrScene = document.getElementById('headerCurrentSceneName');
  if (hdrScene && activeProf) {
    hdrScene.innerText = activeProf.name || state.activeProfile;
  }

  Object.values(state.profiles).filter(p => !p.isFolder).forEach(p => {
    const item = document.createElement('div');
    item.className = `scene-radio-item ${p.id === state.activeProfile ? 'active' : ''}`;
    const appBadge = p.linked_app ? `<span class="scene-app-badge" title="Vinculado ao ${p.linked_app}">${p.linked_app}</span>` : '';
    item.innerHTML = `
      <div class="scene-radio-dot"></div>
      <span class="scene-radio-name">${p.name}</span>
      ${appBadge}
    `;
    item.onclick = () => switchProfile(p.id);

    // Suporte a arrastar tecla de uma tela para outra cena
    item.ondragover = (e) => {
      e.preventDefault();
      item.classList.add('drag-target');
    };
    item.ondragleave = () => {
      item.classList.remove('drag-target');
    };
    item.ondrop = (e) => {
      e.preventDefault();
      item.classList.remove('drag-target');
      const srcSlotStr = e.dataTransfer.getData('text/slot');
      if (srcSlotStr !== '') {
        const srcSlot = parseInt(srcSlotStr);
        copyKeyToScene(srcSlot, p.id);
      }
    };

    container.appendChild(item);
  });
}

// Atualiza informações da Cena no Inspector quando nenhuma tecla está selecionada
function updateSceneInspector() {
  const titleEl = document.getElementById('emptyStateSceneTitle');
  const appEl = document.getElementById('emptyStateLinkedApp');
  const autoSwitchEl = document.getElementById('emptyStateAutoSwitchStatus');
  const activeProf = state.profiles[state.activeProfile];

  if (titleEl && activeProf) {
    titleEl.textContent = activeProf.name;
  }
  if (appEl && activeProf) {
    if (activeProf.linked_app) {
      appEl.textContent = activeProf.linked_app;
      appEl.className = 'scene-prop-val highlight';
    } else {
      appEl.textContent = 'Nenhum (Troca Manual)';
      appEl.className = 'scene-prop-val';
    }
  }
  if (autoSwitchEl) {
    autoSwitchEl.textContent = state.autoSwitchEnabled !== false ? 'Ativado' : 'Desativado';
    autoSwitchEl.className = state.autoSwitchEnabled !== false ? 'scene-prop-val highlight' : 'scene-prop-val';
  }
}

// Copia ou move uma tecla para outra cena
async function copyKeyToScene(srcSlot, targetSceneId) {
  const srcKey = state.profiles[state.activeProfile]?.keys[srcSlot];
  if (!srcKey || !state.profiles[targetSceneId]) return;

  if (!state.profiles[targetSceneId].keys) {
    state.profiles[targetSceneId].keys = {};
  }
  const targetKeys = state.profiles[targetSceneId].keys;

  let targetSlot = -1;
  for (let s = 0; s < 15; s++) {
    if (!targetKeys[s]) {
      targetSlot = s;
      break;
    }
  }
  if (targetSlot === -1) targetSlot = srcSlot;

  targetKeys[targetSlot] = JSON.parse(JSON.stringify(srcKey));
  await switchProfile(targetSceneId);
  selectKey(targetSlot);
  await syncKeyToHardware(targetSlot, targetKeys[targetSlot]);
  showToast(`✓ Tecla transferida para a cena "${state.profiles[targetSceneId].name}"`);
}

// Troca de Perfil instantânea (0ms no browser + sync relâmpago no Stream Deck)
function switchProfile(profileId) {
  state.activeProfile = profileId;
  state.selectedSlot = 0;
  
  // Atualiza imediatamente a interface do usuário (0ms)
  renderSceneList();
  renderDeckGrid();
  selectKey(0);

  const profileName = state.profiles[profileId]?.name || profileId;
  const hdrScene = document.getElementById('headerCurrentSceneName');
  if (hdrScene) hdrScene.innerText = profileName;

  // Dispara sincronização com o hardware imediatamente em background
  fetch('/api/page/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ page: profileId })
  }).then(res => {
    if (res.ok) {
      showToast(`✓ ${profileName} ativa no Stream Deck`);
    }
  }).catch(err => {
    console.error('Falha ao sincronizar troca de cena no hardware:', err);
  });
}

function showToast(msg) {
  const t = document.getElementById('syncToast');
  if (!t) return;
  t.innerText = msg;
  t.style.display = 'flex';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.style.display = 'none'; }, 2500);
}

// Micro-animação tátil de afundamento e retorno (feedback visual de clique no slot)
function triggerKeyAnimation(slotIndex) {
  const el = document.querySelector(`.deck-key-slot[data-slot="${slotIndex}"]`);
  if (el) {
    el.classList.add('is-pressed');
    setTimeout(() => {
      el.classList.remove('is-pressed');
    }, 180);
  }
}

async function executeKeyActionOnMac(slot) {
  const keyData = state.profiles[state.activeProfile]?.keys[slot];
  if (!keyData) return;
  triggerKeyAnimation(slot);
  const act = buildActionPayload(keyData);
  if (!act) return;
  try {
    await fetch('/api/key/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: act, slot: slot + 1, page: state.activeProfile })
    });
    showToast(`▶ Executando "${keyData.title || 'Ação'}" no Mac...`);
  } catch (e) {
    showToast('Erro ao disparar ação no Mac');
  }
}

// Renderiza o conteúdo visual (ícones, imagens, textos e estilos) em um elemento de tecla LCD
function renderKeyVisualContent(keyEl, keyData) {
  if (!keyEl) return;
  keyEl.innerHTML = '';
  keyEl.classList.remove('is-folder', 'is-back-key', 'is-multiaction', 'is-obs');

  if (!keyData) {
    keyEl.style.backgroundColor = '#18181b';
    keyEl.style.border = '';
    keyEl.draggable = false;
    return;
  }

  keyEl.draggable = true;

  if (keyData.actionType === 'folder' || keyData.uuid?.includes('openchild') || keyData.actionUuid?.includes('openchild') || keyData.target?.startsWith('folder_')) {
    keyEl.classList.add('is-folder');
  } else if (keyData.actionType === 'backtoparent' || keyData.uuid?.includes('backtoparent') || keyData.actionUuid?.includes('backtoparent')) {
    keyEl.classList.add('is-back-key');
  } else if (keyData.actionType === 'multiaction' || keyData.uuid?.includes('routine') || keyData.actionUuid?.includes('routine')) {
    keyEl.classList.add('is-multiaction');
  } else if (keyData.actionType === 'obs' || keyData.uuid?.includes('obsstudio') || keyData.actionUuid?.includes('obsstudio')) {
    keyEl.classList.add('is-obs');
  }

  keyEl.style.backgroundColor = keyData.bg || '#18181b';

  if (keyData.borderWidth && keyData.borderWidth > 0) {
    keyEl.style.border = `${keyData.borderWidth}px solid ${keyData.borderColor || '#007aff'}`;
  } else {
    keyEl.style.border = '';
  }

  if (keyData.imagePath) {
    const img = document.createElement('img');
    if (keyData.imageFit === 'contain') {
      img.className = 'key-inner-icon-contain';
    } else {
      img.className = 'key-inner-bg-cover';
    }
    img.src = '/api/image?path=' + encodeURIComponent(keyData.imagePath);
    keyEl.appendChild(img);
  } else if (keyData.icon || keyData.actionType === 'multiaction' || keyData.actionType === 'obs') {
    if (keyData.icon === 'arrow-left' || keyData.actionType === 'backtoparent') {
      const wrap = document.createElement('div');
      wrap.className = 'key-inner-icon-svg';
      wrap.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${keyData.accent || '#007aff'}" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>`;
      keyEl.appendChild(wrap);
    } else if (keyData.icon === 'folder' || keyData.actionType === 'folder') {
      const wrap = document.createElement('div');
      wrap.className = 'key-inner-icon-svg';
      wrap.innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="${keyData.accent || '#f59e0b'}"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`;
      keyEl.appendChild(wrap);
    } else if (keyData.icon === 'multiaction' || keyData.actionType === 'multiaction' || keyData.uuid?.includes('routine')) {
      const wrap = document.createElement('div');
      wrap.className = 'key-inner-icon-svg';
      wrap.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${keyData.accent || '#a855f7'}" stroke-width="2.5"><polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/></svg>`;
      keyEl.appendChild(wrap);
    } else if (keyData.actionType === 'obs' || keyData.uuid?.includes('obsstudio')) {
      const wrap = document.createElement('div');
      wrap.className = 'key-inner-icon-svg';
      wrap.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${keyData.accent || '#007aff'}" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/></svg>`;
      keyEl.appendChild(wrap);
    } else if (keyData.icon && (keyData.icon.startsWith('/') || keyData.icon.startsWith('http') || keyData.icon.includes('.'))) {
      const img = document.createElement('img');
      img.className = 'key-inner-icon-contain';
      img.src = keyData.icon;
      keyEl.appendChild(img);
    }
  }

  // Renderização de Título e Subtítulo idêntica à tela LCD física
  if (keyData.showTitle !== false && (keyData.title || keyData.subtitle)) {
    const textWrap = document.createElement('div');
    textWrap.className = 'key-inner-text-wrap';
    if (keyData.titleAlignment === 'top') {
      textWrap.classList.add('align-top');
    } else if (keyData.titleAlignment === 'bottom') {
      textWrap.classList.add('align-bottom');
    } else {
      textWrap.classList.add('align-middle');
    }

    if (keyData.title) {
      const lines = String(keyData.title).split('\n').filter(l => l.trim().length > 0);
      if (lines.length > 1) {
        lines.forEach((lineText) => {
          const lineEl = document.createElement('span');
          lineEl.className = 'key-inner-title-line';
          lineEl.innerText = lineText;
          if (keyData.textColor) lineEl.style.color = keyData.textColor;
          if (keyData.fontFamily) lineEl.style.fontFamily = keyData.fontFamily;
          if (keyData.bold) lineEl.style.fontWeight = '700';
          if (keyData.italic) lineEl.style.fontStyle = 'italic';
          if (keyData.underline) lineEl.style.textDecoration = 'underline';
          if (keyData.fontSize) lineEl.style.fontSize = (parseInt(keyData.fontSize) || 11) + 'px';
          textWrap.appendChild(lineEl);
        });
      } else {
        const titleEl = document.createElement('span');
        titleEl.className = 'key-inner-title';
        titleEl.innerText = keyData.title;
        if (keyData.textColor) titleEl.style.color = keyData.textColor;
        if (keyData.fontFamily) titleEl.style.fontFamily = keyData.fontFamily;
        if (keyData.bold) titleEl.style.fontWeight = '700';
        if (keyData.italic) titleEl.style.fontStyle = 'italic';
        if (keyData.underline) titleEl.style.textDecoration = 'underline';
        if (keyData.fontSize) titleEl.style.fontSize = (parseInt(keyData.fontSize) || 11) + 'px';
        textWrap.appendChild(titleEl);
      }
    }

    if (keyData.subtitle) {
      const subEl = document.createElement('span');
      subEl.className = 'key-inner-subtitle';
      subEl.innerText = keyData.subtitle;
      textWrap.appendChild(subEl);
    }

    keyEl.appendChild(textWrap);
  }
}

// Atualiza cirurgicamente a tecla na grade e na miniatura do inspector em tempo real (0ms)
function updateSlotVisual(slot, keyData) {
  if (state.profiles[state.activeProfile]) {
    if (!state.profiles[state.activeProfile].keys) {
      state.profiles[state.activeProfile].keys = {};
    }
    state.profiles[state.activeProfile].keys[slot] = keyData;
  }

  // Atualiza div da grade
  const keyEl = document.querySelector(`.deck-key-slot[data-slot="${slot}"]`);
  if (keyEl) {
    renderKeyVisualContent(keyEl, keyData);
  }

  // Se for o slot selecionado, atualiza também a miniatura e o preview do inspector
  if (slot === state.selectedSlot && keyData) {
    const previewCard = document.getElementById('keyPreviewCard');
    if (previewCard) {
      previewCard.style.backgroundColor = keyData.bg || '#18181b';
      if (keyData.borderWidth && keyData.borderWidth > 0) {
        previewCard.style.border = `${keyData.borderWidth}px solid ${keyData.borderColor || '#007aff'}`;
      } else {
        previewCard.style.border = '1px solid var(--border-subtle)';
      }

      let imgPreview = previewCard.querySelector('.preview-card-img');
      if (keyData.imagePath) {
        if (!imgPreview) {
          imgPreview = document.createElement('img');
          imgPreview.className = 'preview-card-img';
          previewCard.insertBefore(imgPreview, previewCard.firstChild);
        }
        imgPreview.src = '/api/image?path=' + encodeURIComponent(keyData.imagePath);
        imgPreview.style.objectFit = keyData.imageFit || 'cover';
        imgPreview.style.display = 'block';
      } else if (imgPreview) {
        imgPreview.style.display = 'none';
      }
    }

    const prevLabel = document.getElementById('previewKeyLabel');
    if (prevLabel) {
      prevLabel.innerText = keyData.title || '';
      prevLabel.style.display = keyData.showTitle === false ? 'none' : 'block';
      if (keyData.fontFamily) prevLabel.style.fontFamily = keyData.fontFamily;
      prevLabel.style.fontWeight = keyData.bold ? '700' : 'normal';
      prevLabel.style.fontStyle = keyData.italic ? 'italic' : 'normal';
      prevLabel.style.textDecoration = keyData.underline ? 'underline' : 'none';
    }

    const prevSub = document.getElementById('previewKeySub');
    if (prevSub) {
      prevSub.innerText = keyData.subtitle || '';
      prevSub.style.display = (keyData.showTitle !== false && keyData.subtitle) ? 'block' : 'none';
    }
  }
}

// Renderiza as 15 Teclas do Deck com Drag-and-Drop 1:1, Duplicação e Menu de Contexto
function renderDeckGrid() {
  const grid = document.getElementById('deckGrid');
  if (!grid) return;
  grid.innerHTML = '';

  // Breadcrumb de Pasta (com suporte a trilha hierárquica multi-nível)
  const breadcrumb = document.getElementById('folderBreadcrumb');
  const currentProfile = state.profiles[state.activeProfile];
  if (breadcrumb) {
    if (currentProfile && (currentProfile.isFolder || currentProfile.parentPage)) {
      breadcrumb.style.display = 'flex';

      const pathTrail = [];
      let cur = currentProfile;
      while (cur) {
        pathTrail.unshift(cur);
        cur = cur.parentPage && state.profiles[cur.parentPage] ? state.profiles[cur.parentPage] : null;
      }

      const crumbPathEl = document.getElementById('folderCrumbPath');
      if (crumbPathEl) {
        crumbPathEl.innerHTML = '';
        pathTrail.forEach((node, idx) => {
          if (idx > 0) {
            const sep = document.createElement('span');
            sep.className = 'crumb-sep';
            sep.innerText = '/';
            crumbPathEl.appendChild(sep);
          }
          const itemEl = document.createElement('span');
          if (idx === pathTrail.length - 1) {
            itemEl.className = 'crumb-active';
            itemEl.innerText = node.name;
          } else {
            itemEl.className = 'crumb-root';
            itemEl.innerText = node.name;
            itemEl.onclick = () => switchProfile(node.id);
          }
          crumbPathEl.appendChild(itemEl);
        });
      }

      const backBtn = document.getElementById('btnBreadcrumbBack');
      if (backBtn) {
        backBtn.onclick = () => goBackParent();
      }
    } else {
      breadcrumb.style.display = 'none';
    }
  }

  const activeKeys = currentProfile?.keys || {};

  for (let slot = 0; slot < 15; slot++) {
    const keyData = activeKeys[slot];
    const keyEl = document.createElement('div');
    keyEl.className = `deck-key-slot ${slot === state.selectedSlot ? 'selected' : ''}`;
    keyEl.dataset.slot = slot;

    renderKeyVisualContent(keyEl, keyData);

    keyEl.ondragstart = (e) => {
      e.dataTransfer.setData('text/slot', slot.toString());
      e.dataTransfer.effectAllowed = 'copyMove';
      keyEl.classList.add('dragging');
    };

    keyEl.ondragend = () => {
      keyEl.classList.remove('dragging');
      document.querySelectorAll('.deck-key-slot').forEach(el => el.classList.remove('drag-target'));
    };

    // Feedback tátil imediato de clique / afundamento com o mouse
    keyEl.onmousedown = (e) => {
      if (e.button === 0) {
        triggerKeyAnimation(slot);
      }
    };

    // Clique com botão esquerdo para selecionar
    keyEl.onclick = () => selectKey(slot);

    // Duplo clique: se for pasta entra; se for ação, executa imediatamente no Mac!
    keyEl.ondblclick = () => {
      const curData = state.profiles[state.activeProfile]?.keys?.[slot];
      if (!curData) return;
      if (keyData.actionType === 'folder' || keyData.uuid?.includes('openchild') || keyData.actionUuid?.includes('openchild') || keyData.target?.startsWith('folder_')) {
        openFolder(keyData.target || keyData.folderId);
      } else if (keyData.actionType === 'backtoparent' || keyData.uuid?.includes('backtoparent') || keyData.actionUuid?.includes('backtoparent')) {
        goBackParent();
      } else {
        executeKeyActionOnMac(slot);
      }
    };

    // Clique com botão direito para abrir Menu de Contexto (Copiar / Colar / Duplicar / Excluir)
    keyEl.oncontextmenu = (e) => {
      e.preventDefault();
      e.stopPropagation();
      selectKey(slot);
      showSlotContextMenu(e.clientX, e.clientY, slot);
    };

    // Suporte completo a Drag-and-Drop (de tecla para tecla, do catálogo, ou do Finder)
    keyEl.ondragover = (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = e.altKey ? 'copy' : 'move';
      keyEl.classList.add('drag-target');
    };

    keyEl.ondragleave = () => {
      keyEl.classList.remove('drag-target');
    };

    keyEl.ondrop = (e) => {
      e.preventDefault();
      keyEl.classList.remove('drag-target');

      // 1. Mover, Trocar ou Duplicar tecla de outro slot
      const srcSlotStr = e.dataTransfer.getData('text/slot');
      if (srcSlotStr !== '') {
        const srcSlot = parseInt(srcSlotStr);
        if (srcSlot !== slot) {
          moveOrSwapSlots(srcSlot, slot, e.altKey);
        }
        return;
      }

      // 2. Ação vinda do catálogo lateral
      const actionDataRaw = e.dataTransfer.getData('application/json');
      if (actionDataRaw) {
        try {
          const actionData = JSON.parse(actionDataRaw);
          assignActionToSlot(slot, actionData);
        } catch (err) {}
        return;
      }

      // 3. Arquivo arrastado diretamente do Finder do macOS
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleDroppedFile(slot, e.dataTransfer.files[0]);
      }
    };

    grid.appendChild(keyEl);
  }
}

// Move ou troca teclas entre dois slots (ou duplica se isCopy for true)
function moveOrSwapSlots(srcSlot, dstSlot, isCopy = false) {
  const profile = state.profiles[state.activeProfile];
  if (!profile || !profile.keys) return;

  // Protege a tecla de retorno VOLTAR no slot 0 de pastas
  if (profile.isFolder && (dstSlot === 0 || srcSlot === 0)) {
    const isBackKey = (profile.keys[0]?.actionType === 'backtoparent' || profile.keys[0]?.actionUuid?.includes('backtoparent'));
    if (isBackKey) {
      showToast('O primeiro slot de uma pasta é reservado para a navegação de retorno ("VOLTAR").');
      return;
    }
  }

  const srcData = profile.keys[srcSlot];
  if (!srcData) return;

  const dstData = profile.keys[dstSlot];

  if (isCopy) {
    profile.keys[dstSlot] = JSON.parse(JSON.stringify(srcData));
    showToast(`✓ Tecla duplicada para o slot ${dstSlot + 1}`);
    syncKeyToHardware(dstSlot, profile.keys[dstSlot]);
  } else {
    if (dstData) {
      // Inversão (Swap) de posições
      profile.keys[dstSlot] = srcData;
      profile.keys[srcSlot] = dstData;
      showToast(`✓ Teclas ${srcSlot + 1} e ${dstSlot + 1} trocadas de posição`);
      syncKeyToHardware(srcSlot, profile.keys[srcSlot]);
      syncKeyToHardware(dstSlot, profile.keys[dstSlot]);
    } else {
      // Move para slot vazio
      profile.keys[dstSlot] = srcData;
      delete profile.keys[srcSlot];
      showToast(`✓ Tecla movida para o slot ${dstSlot + 1}`);
      syncKeyToHardware(srcSlot, null);
      syncKeyToHardware(dstSlot, profile.keys[dstSlot]);
    }
  }

  renderDeckGrid();
  selectKey(dstSlot);
}

// Copiar tecla (⌘C)
function copyKey(slot) {
  const keyData = state.profiles[state.activeProfile]?.keys[slot];
  if (keyData) {
    state.clipboard = JSON.parse(JSON.stringify(keyData));
    showToast(`✓ Tecla ${slot + 1} copiada (⌘C)`);
  }
}

// Colar tecla (⌘V)
function pasteKey(slot) {
  if (!state.clipboard) {
    showToast('Nenhuma tecla copiada na área de transferência.');
    return;
  }
  const profile = state.profiles[state.activeProfile];
  if (!profile.keys) profile.keys = {};

  profile.keys[slot] = JSON.parse(JSON.stringify(state.clipboard));
  renderDeckGrid();
  selectKey(slot);
  syncKeyToHardware(slot, profile.keys[slot]);
  showToast(`✓ Tecla colada no slot ${slot + 1} (⌘V)`);
}

// Recortar tecla (⌘X)
function cutKey(slot) {
  copyKey(slot);
  deleteKey(slot);
  showToast(`✓ Tecla ${slot + 1} recortada (⌘X)`);
}

// Duplicar tecla
function duplicateKey(slot) {
  const keyData = state.profiles[state.activeProfile]?.keys[slot];
  if (!keyData) return;

  const keys = state.profiles[state.activeProfile].keys;
  let targetSlot = -1;
  for (let s = slot + 1; s < 15; s++) {
    if (!keys[s]) { targetSlot = s; break; }
  }
  if (targetSlot === -1) {
    for (let s = 0; s < 15; s++) {
      if (!keys[s]) { targetSlot = s; break; }
    }
  }
  if (targetSlot === -1) {
    showToast('Não há slots vazios para duplicar.');
    return;
  }

  keys[targetSlot] = JSON.parse(JSON.stringify(keyData));
  renderDeckGrid();
  selectKey(targetSlot);
  syncKeyToHardware(targetSlot, keys[targetSlot]);
  showToast(`✓ Tecla duplicada no slot ${targetSlot + 1}`);
}

// Excluir tecla (⌫)
function deleteKey(slot) {
  const profile = state.profiles[state.activeProfile];
  if (!profile || !profile.keys[slot]) return;

  const keyData = profile.keys[slot];

  // 1. Impede exclusão da tecla VOLTAR em Slot 0 dentro de uma pasta
  if (profile.isFolder && slot === 0 && (keyData.actionType === 'backtoparent' || keyData.actionUuid?.includes('backtoparent'))) {
    showToast('A tecla "VOLTAR" é essencial para navegar e não pode ser excluída.');
    return;
  }

  // 2. Se a tecla for uma Pasta, limpa a sub-página associada
  const targetFolderId = keyData.target || keyData.folderId;
  if ((keyData.actionType === 'folder' || keyData.actionUuid?.includes('openchild')) && targetFolderId) {
    if (state.profiles[targetFolderId]) {
      delete state.profiles[targetFolderId];
    }
    fetch('/api/page/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: targetFolderId })
    }).catch(() => {});
  }

  delete profile.keys[slot];
  renderDeckGrid();
  selectKey(slot);
  syncKeyToHardware(slot, null);
  showToast(`✓ Ação do slot ${slot + 1} excluída`);
}

// Exibe menu de contexto flutuante com botão direito
function showSlotContextMenu(x, y, slot) {
  const menu = document.getElementById('slotContextMenu');
  if (!menu) return;

  const keyData = state.profiles[state.activeProfile]?.keys[slot];
  const isBackKey = keyData && (keyData.actionType === 'backtoparent' || keyData.actionUuid?.includes('backtoparent'));

  const itemCopy = document.getElementById('ctxMenuCopy');
  const itemPaste = document.getElementById('ctxMenuPaste');
  const itemDup = document.getElementById('ctxMenuDuplicate');
  const itemDel = document.getElementById('ctxMenuDelete');

  if (itemCopy) itemCopy.classList.toggle('disabled', !keyData || isBackKey);
  if (itemDup) itemDup.classList.toggle('disabled', !keyData || isBackKey);
  if (itemDel) itemDel.classList.toggle('disabled', !keyData || isBackKey);
  if (itemPaste) itemPaste.classList.toggle('disabled', !state.clipboard || isBackKey);

  menu.style.display = 'flex';
  menu.style.left = `${Math.min(x, window.innerWidth - 185)}px`;
  menu.style.top = `${Math.min(y, window.innerHeight - 160)}px`;

  itemCopy.onclick = () => { menu.style.display = 'none'; copyKey(slot); };
  itemPaste.onclick = () => { menu.style.display = 'none'; pasteKey(slot); };
  itemDup.onclick = () => { menu.style.display = 'none'; duplicateKey(slot); };
  itemDel.onclick = () => { menu.style.display = 'none'; deleteKey(slot); };
}

// Processa arquivo ou imagem arrastada do Finder diretamente sobre a tecla
async function handleDroppedFile(slot, file) {
  if (!file) return;
  const isImage = file.type.startsWith('image/') || /\.(png|jpe?g|gif|svg|webp)$/i.test(file.name);

  if (!state.profiles[state.activeProfile].keys) {
    state.profiles[state.activeProfile].keys = {};
  }

  if (isImage) {
    const reader = new FileReader();
    reader.onload = async (e) => {
      const b64 = e.target.result;
      showToast('Enviando imagem...');
      try {
        const res = await fetch('/api/upload_image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: file.name, base64: b64 })
        });
        const data = await res.json();
        if (data.success && data.path) {
          if (!state.profiles[state.activeProfile].keys[slot]) {
            state.profiles[state.activeProfile].keys[slot] = {
              title: '',
              bg: '#18181b',
              textColor: '#ffffff',
              category: 'Geral',
              actionType: 'none',
              actionName: 'Imagem'
            };
          }
          const kData = state.profiles[state.activeProfile].keys[slot];
          kData.imagePath = data.path;
          renderDeckGrid();
          selectKey(slot);
          syncKeyToHardware(slot, kData);
          showToast('✓ Imagem aplicada à tecla!');
        }
      } catch (err) {
        showToast('Erro ao carregar imagem');
      }
    };
    reader.readAsDataURL(file);
  } else {
    const appName = file.name.replace('.app', '');
    const appPath = file.path || `/Applications/${file.name}`;
    state.profiles[state.activeProfile].keys[slot] = {
      title: appName,
      bg: '#18181b',
      textColor: '#ffffff',
      category: 'Caixa de Ferramentas',
      actionType: 'open',
      actionName: 'Abra uma aplicação',
      path: appPath,
      textPayload: '',
      pressEnter: false,
      useClipboard: true,
      icon: '',
      imagePath: ''
    };
    renderDeckGrid();
    selectKey(slot);
    syncKeyToHardware(slot, state.profiles[state.activeProfile].keys[slot]);
    showToast(`✓ Aplicação "${appName}" configurada no slot ${slot + 1}!`);
  }
}

// Seleciona uma tecla e abre o Property Inspector correspondente
function selectKey(slot) {
  state.selectedSlot = slot;

  // Garante que a aba de Propriedades na barra direita seja ativada
  switchRightTab('tabPaneInspector');

  // Atualiza classe selected nas teclas
  document.querySelectorAll('.deck-key-slot').forEach(el => {
    el.classList.toggle('selected', parseInt(el.dataset.slot) === slot);
  });

  const activeKeys = state.profiles[state.activeProfile]?.keys || {};
  let keyData = activeKeys[slot];

  const emptyState = document.getElementById('inspectorEmptyState');
  const activeContent = document.getElementById('inspectorActiveContent');

  if (!keyData) {
    if (!state.profiles[state.activeProfile]) return;
    if (!state.profiles[state.activeProfile].keys) {
      state.profiles[state.activeProfile].keys = {};
    }
    state.profiles[state.activeProfile].keys[slot] = {
      title: '',
      subtitle: '',
      bg: '#18181b',
      textColor: '#ffffff',
      fontSize: 12,
      actionType: 'none',
      showTitle: true
    };
    keyData = state.profiles[state.activeProfile].keys[slot];
  }

  emptyState.style.display = 'none';
  activeContent.style.display = 'flex';

  // Cabeçalho: Categoria : Ação
  const catTitle = document.getElementById('inspectorActionCategory');
  catTitle.innerText = `${keyData.category || 'Caixa de Ferramentas'} : ${keyData.actionName || 'Ação'}`;

  // Miniatura
  const previewCard = document.getElementById('keyPreviewCard');
  previewCard.style.backgroundColor = keyData.bg || '#004481';
  if (keyData.borderWidth && keyData.borderWidth > 0) {
    previewCard.style.border = `${keyData.borderWidth}px solid ${keyData.borderColor || '#007aff'}`;
  } else {
    previewCard.style.border = '1px solid var(--border-subtle)';
  }

  // Sincroniza cor LCD e indicadores
  const curBg = keyData.bg || '#18181b';
  document.querySelectorAll('.swatch:not(.scene-swatch)').forEach(b => {
    b.classList.toggle('active', (b.dataset.color || '').toLowerCase() === curBg.toLowerCase());
  });
  const cp = document.getElementById('customColorPicker');
  if (cp) cp.value = curBg;
  const hexLbl = document.getElementById('currentColorHex');
  if (hexLbl) hexLbl.innerText = curBg;

  let imgPreview = previewCard.querySelector('.preview-card-img');
  if (keyData.imagePath) {
    if (!imgPreview) {
      imgPreview = document.createElement('img');
      imgPreview.className = 'preview-card-img';
      previewCard.insertBefore(imgPreview, previewCard.firstChild);
    }
    imgPreview.src = '/api/image?path=' + encodeURIComponent(keyData.imagePath);
    imgPreview.style.objectFit = keyData.imageFit || 'cover';
    imgPreview.style.display = 'block';
  } else if (imgPreview) {
    imgPreview.style.display = 'none';
  }

  const previewLabel = document.getElementById('previewKeyLabel');
  const previewSub = document.getElementById('previewKeySub');
  if (keyData.showTitle === false) {
    previewLabel.style.display = 'none';
    if (previewSub) previewSub.style.display = 'none';
  } else {
    previewLabel.style.display = 'block';
    previewLabel.innerText = keyData.title || '';
    previewLabel.style.fontFamily = keyData.fontFamily || 'Helvetica';
    previewLabel.style.fontWeight = keyData.bold ? '700' : 'normal';
    previewLabel.style.fontStyle = keyData.italic ? 'italic' : 'normal';
    previewLabel.style.textDecoration = keyData.underline ? 'underline' : 'none';

    if (previewSub) {
      if (keyData.subtitle) {
        previewSub.style.display = 'block';
        previewSub.innerText = keyData.subtitle;
      } else {
        previewSub.style.display = 'none';
      }
    }
  }

  // Campo Título
  const inputTitle = document.getElementById('inputKeyTitle');
  inputTitle.value = keyData.title || '';

  // Campo Subtítulo
  const inputSubtitle = document.getElementById('inputKeySubtitle');
  if (inputSubtitle) inputSubtitle.value = keyData.subtitle || '';

  // Popover Tipográfico (Carrega valores salvos da tecla)
  const selFont = document.getElementById('selectFontFamily');
  if (selFont) selFont.value = keyData.fontFamily || 'Helvetica';

  const selSize = document.getElementById('selectFontSize');
  if (selSize) selSize.value = (parseInt(keyData.fontSize) || 12).toString();

  document.getElementById('btnStyleBold')?.classList.toggle('active', !!keyData.bold);
  document.getElementById('btnStyleItalic')?.classList.toggle('active', !!keyData.italic);
  document.getElementById('btnStyleUnderline')?.classList.toggle('active', !!keyData.underline);

  const curAlign = keyData.titleAlignment || 'middle';
  document.getElementById('btnAlignTop')?.classList.toggle('active', curAlign === 'top');
  document.getElementById('btnAlignMiddle')?.classList.toggle('active', curAlign === 'middle');
  document.getElementById('btnAlignBottom')?.classList.toggle('active', curAlign === 'bottom');

  const chkHide = document.getElementById('chkDoNotShowTitle');
  if (chkHide) chkHide.checked = keyData.showTitle === false;

  // Borda LCD
  const selBw = document.getElementById('selectBorderWidth');
  if (selBw) selBw.value = (keyData.borderWidth !== undefined ? keyData.borderWidth : 0).toString();

  const inpBc = document.getElementById('inputBorderColor');
  if (inpBc) inpBc.value = keyData.borderColor || '#007aff';

  // Ícone / Imagem
  const selFit = document.getElementById('selectImageFit');
  if (selFit) selFit.value = keyData.imageFit || 'cover';

  const btnRemImg = document.getElementById('btnRemoveKeyImage');
  if (btnRemImg) btnRemImg.style.display = (keyData.imagePath || keyData.icon) ? 'block' : 'none';

  // Painéis Contextuais por Tipo de Ação
  const ctxText = document.getElementById('fieldsContextText');
  const ctxOpen = document.getElementById('fieldsContextOpen');
  const ctxHotkey = document.getElementById('fieldsContextHotkey');
  const ctxUrl = document.getElementById('fieldsContextUrl');
  const ctxObs = document.getElementById('fieldsContextObs');
  const ctxSound = document.getElementById('fieldsContextSoundboard');
  const ctxShell = document.getElementById('fieldsContextShell');
  const ctxToggle = document.getElementById('fieldsContextToggle');

  ctxText.style.display = 'none';
  ctxOpen.style.display = 'none';
  ctxHotkey.style.display = 'none';
  ctxUrl.style.display = 'none';
  if (ctxObs) ctxObs.style.display = 'none';
  if (ctxSound) ctxSound.style.display = 'none';
  if (ctxShell) ctxShell.style.display = 'none';
  if (ctxToggle) ctxToggle.style.display = 'none';

  if (keyData.actionType === 'text') {
    ctxText.style.display = 'block';
    const txt = document.getElementById('inputTextPayload');
    txt.value = keyData.textPayload || '';
    updateCharCounter(txt.value.length);
    document.getElementById('chkPressEnter').checked = !!keyData.pressEnter;
    document.getElementById('chkUseClipboard').checked = keyData.useClipboard !== false;
  } else if (keyData.actionType === 'open') {
    ctxOpen.style.display = 'block';
    document.getElementById('inputOpenPath').value = keyData.path || '';
  } else if (keyData.actionType === 'soundboard' || keyData.uuid?.includes('soundboard') || keyData.actionUuid?.includes('soundboard') || keyData.uuid?.includes('playaudio')) {
    if (ctxSound) {
      ctxSound.style.display = 'block';
      const inputSound = document.getElementById('inputSoundboardPath');
      if (inputSound) inputSound.value = keyData.path || keyData.target || '';
    }
  } else if (keyData.actionType === 'shell' || keyData.actionType === 'shell_command' || keyData.uuid?.includes('shell')) {
    if (ctxShell) {
      ctxShell.style.display = 'block';
      const inputShell = document.getElementById('inputShellCommand');
      if (inputShell) inputShell.value = keyData.command || keyData.cmd || keyData.path || '';
    }
  } else if (keyData.actionType === 'toggle' || keyData.uuid?.includes('toggle') || keyData.uuid?.includes('hotkeySwitch')) {
    if (ctxToggle) {
      ctxToggle.style.display = 'block';
      const tA = document.getElementById('inputToggleTitleA');
      const kA = document.getElementById('inputToggleKeysA');
      const tB = document.getElementById('inputToggleTitleB');
      const kB = document.getElementById('inputToggleKeysB');
      if (tA) tA.value = keyData.title_a || keyData.title || '';
      if (kA) kA.value = keyData.keys_a || '';
      if (tB) tB.value = keyData.title_b || '';
      if (kB) kB.value = keyData.keys_b || '';
    }
  } else if (keyData.actionType === 'hotkey') {
    ctxHotkey.style.display = 'block';
    document.getElementById('hotkeyBadge').innerText = keyData.hotkey || 'Pressione para gravar';
  } else if (keyData.actionType === 'url') {
    ctxUrl.style.display = 'block';
    document.getElementById('inputUrlTarget').value = keyData.url || '';
  } else if (keyData.actionType === 'obs' || keyData.uuid?.includes('obsstudio') || keyData.actionUuid?.includes('obsstudio')) {
    if (ctxObs) {
      ctxObs.style.display = 'block';
      updateObsContextPanel(keyData);
    }
  } else if (keyData.actionType === 'folder' || keyData.uuid?.includes('openchild') || keyData.actionUuid?.includes('openchild') || keyData.target?.startsWith('folder_')) {
    const ctxFolder = document.getElementById('fieldsContextFolder');
    if (ctxFolder) {
      ctxFolder.style.display = 'block';
      const btnEnter = document.getElementById('btnEnterFolder');
      if (btnEnter) {
        btnEnter.onclick = () => openFolder(keyData.target || keyData.folderId);
      }
    }
  } else if (keyData.actionType === 'backtoparent' || keyData.uuid?.includes('backtoparent') || keyData.actionUuid?.includes('backtoparent')) {
    const ctxBack = document.getElementById('fieldsContextBack');
    if (ctxBack) {
      ctxBack.style.display = 'block';
      const btnBack = document.getElementById('btnGoBackParent');
      if (btnBack) {
        btnBack.onclick = () => goBackParent();
      }
    }
  } else if (keyData.actionType === 'multiaction' || keyData.uuid?.includes('routine') || keyData.actionUuid?.includes('routine')) {
    const ctxMulti = document.getElementById('fieldsContextMulti');
    if (ctxMulti) {
      ctxMulti.style.display = 'block';
      renderMultiSteps(keyData);
    }
  }
}

// Atribui ação à tecla via Drag-and-Drop
function assignActionToSlot(slot, action) {
  const profile = state.profiles[state.activeProfile];
  if (!profile.keys) profile.keys = {};

  // Protege a tecla de retorno VOLTAR no slot 0 de pastas
  if (profile.isFolder && slot === 0) {
    showToast('O primeiro slot de uma pasta é reservado para a navegação de retorno ("VOLTAR").');
    return;
  }

  const actionType = getActionTypeFromUuid(action.uuid);

  // Se a ação for criar pasta
  if (actionType === 'folder' || action.uuid?.includes('openchild') || action.name === 'Criar Pasta') {
    createFolderForSlot(slot);
    return;
  }

  // Se a ação for Multi-Ação / Sequência de Macros
  if (actionType === 'multiaction' || action.uuid?.includes('routine') || action.name === 'Ação Múltipla') {
    profile.keys[slot] = {
      title: 'MACRO',
      subtitle: 'Multi-Ação',
      bg: '#18181b',
      textColor: '#ffffff',
      accent: '#a855f7',
      fontSize: '12px',
      icon: 'multiaction',
      actionType: 'multiaction',
      actionUuid: 'com.hotspot.streamdock.multiactions.routine',
      uuid: 'com.hotspot.streamdock.multiactions.routine',
      category: 'Fluxo de Operação',
      actionName: 'Ação Múltipla',
      steps: [
        { type: 'open', target: '/Applications/Safari.app', delay: 300 },
        { type: 'delay', delay: 500 },
        { type: 'text', text: 'https://google.com', enter: true }
      ]
    };
    renderDeckGrid();
    selectKey(slot);
    syncKeyToHardware(slot, profile.keys[slot]);
    showToast(`✓ Multi-Ação configurada no slot ${slot + 1}`);
    return;
  }

  // Se a ação for OBS Studio WebSocket v5
  if (actionType === 'obs' || action.uuid?.includes('obsstudio') || action.uuid?.startsWith('obs_')) {
    const sub = action.uuid.split('.').pop() || 'action';
    let defaultTitle = action.name || 'OBS';
    let defaultAccent = '#007aff';
    if (sub === 'record') {
      defaultTitle = 'REC';
      defaultAccent = '#ef4444';
    } else if (sub === 'stream') {
      defaultTitle = 'STREAM';
      defaultAccent = '#10b981';
    } else if (sub === 'mixeraudio') {
      defaultTitle = 'AUDIO';
      defaultAccent = '#10b981';
    } else if (sub === 'virtualcamera') {
      defaultTitle = 'CAM';
      defaultAccent = '#06b6d4';
    } else if (sub === 'studiomode') {
      defaultTitle = 'STUDIO';
      defaultAccent = '#a855f7';
    } else if (sub === 'screenshot') {
      defaultTitle = 'PRINT';
      defaultAccent = '#eab308';
    }

    profile.keys[slot] = {
      title: defaultTitle,
      subtitle: '',
      bg: '#18181b',
      textColor: '#ffffff',
      accent: defaultAccent,
      fontSize: '12px',
      icon: 'obs',
      actionType: 'obs',
      actionUuid: action.uuid,
      uuid: action.uuid,
      category: 'OBS Studio',
      actionName: action.name || 'Ação OBS',
      sceneName: '',
      sourceName: '',
      sceneItemId: null,
      visible: true
    };
    renderDeckGrid();
    selectKey(slot);
    syncKeyToHardware(slot, profile.keys[slot]);
    showToast(`✓ Ação OBS "${action.name}" configurada no slot ${slot + 1}`);
    return;
  }

  // Se a ação for Soundboard (Áudio)
  if (actionType === 'soundboard' || action.uuid?.includes('soundboard') || action.uuid?.includes('audioplay')) {
    const isStop = action.uuid?.includes('stopaudioplay');
    profile.keys[slot] = {
      title: isStop ? 'PARAR\nSOM' : (action.name || 'TOCAR SOM'),
      subtitle: isStop ? 'Stop' : 'Áudio',
      bg: isStop ? '#7f1d1d' : '#1e1b4b',
      textColor: '#ffffff',
      accent: isStop ? '#ef4444' : '#818cf8',
      fontSize: '12px',
      icon: isStop ? 'square' : 'play',
      actionType: 'soundboard',
      actionUuid: action.uuid,
      uuid: action.uuid,
      category: 'Reprodutor de Áudio',
      actionName: action.name || 'Áudio',
      path: ''
    };
    renderDeckGrid();
    selectKey(slot);
    syncKeyToHardware(slot, profile.keys[slot]);
    showToast(`✓ Ação de Áudio configurada no slot ${slot + 1}`);
    return;
  }

  // Se a ação for Comando Shell / Terminal
  if (actionType === 'shell' || action.uuid?.includes('shell')) {
    profile.keys[slot] = {
      title: 'TERMINAL',
      subtitle: 'Shell',
      bg: '#0f172a',
      textColor: '#ffffff',
      accent: '#38bdf8',
      fontSize: '12px',
      icon: 'terminal',
      actionType: 'shell',
      actionUuid: action.uuid || 'com.hotspot.streamdock.system.shell',
      uuid: action.uuid || 'com.hotspot.streamdock.system.shell',
      category: 'Caixa de Ferramentas',
      actionName: 'Comando Shell',
      command: 'open -a Safari'
    };
    renderDeckGrid();
    selectKey(slot);
    syncKeyToHardware(slot, profile.keys[slot]);
    showToast(`✓ Comando Shell configurado no slot ${slot + 1}`);
    return;
  }

  // Se a ação for Alternância A/B (Toggle)
  if (actionType === 'toggle' || action.uuid?.includes('toggle')) {
    profile.keys[slot] = {
      title: 'MIC ON',
      subtitle: 'Toggle',
      bg: '#14532d',
      textColor: '#ffffff',
      accent: '#22c55e',
      fontSize: '12px',
      icon: 'toggle',
      actionType: 'toggle',
      actionUuid: action.uuid || 'com.hotspot.streamdock.system.toggle',
      uuid: action.uuid || 'com.hotspot.streamdock.system.toggle',
      category: 'Caixa de Ferramentas',
      actionName: 'Alternância A/B',
      title_a: 'MIC ON',
      title_b: 'MUTED',
      bg_a: '#14532d',
      bg_b: '#7f1d1d',
      accent_a: '#22c55e',
      accent_b: '#ef4444',
      keys_a: 'Cmd+Shift+M',
      keys_b: 'Cmd+Shift+M',
      current_state: 0
    };
    renderDeckGrid();
    selectKey(slot);
    syncKeyToHardware(slot, profile.keys[slot]);
    showToast(`✓ Tecla Toggle A/B configurada no slot ${slot + 1}`);
    return;
  }

  // Controles de Janelas & Sistema macOS
  if (actionType.startsWith('close_') || actionType.includes('window') || actionType.includes('lock') || actionType.includes('desktop')) {
    let title = action.name || 'SISTEMA';
    let accent = '#f59e0b';
    if (actionType === 'close_window') { title = 'FECHAR\nJANELA'; accent = '#ef4444'; }
    else if (actionType === 'close_app') { title = 'FECHAR\nAPP'; accent = '#dc2626'; }
    else if (actionType === 'minimize_window') { title = 'MINIMIZAR'; accent = '#eab308'; }
    else if (actionType === 'fullscreen_toggle') { title = 'TELA\nCHEIA'; accent = '#3b82f6'; }
    else if (actionType === 'lock_screen') { title = 'BLOQUEAR\nMAC'; accent = '#6366f1'; }
    else if (actionType === 'show_desktop') { title = 'MOSTRAR\nMESA'; accent = '#06b6d4'; }

    profile.keys[slot] = {
      title: title,
      subtitle: 'macOS',
      bg: '#18181b',
      textColor: '#ffffff',
      accent: accent,
      fontSize: '12px',
      actionType: actionType,
      actionUuid: action.uuid,
      uuid: action.uuid,
      category: 'Touchbar',
      actionName: action.name || 'Controle macOS'
    };
    renderDeckGrid();
    selectKey(slot);
    syncKeyToHardware(slot, profile.keys[slot]);
    showToast(`✓ ${action.name} configurado no slot ${slot + 1}`);
    return;
  }

  profile.keys[slot] = {
    title: action.name || 'Nova Ação',
    uuid: action.uuid || '',
    category: action.category || 'Caixa de Ferramentas',
    actionType: actionType,
    actionUuid: action.uuid || '',
    actionName: action.name || 'Ação',
    textPayload: '',
    pressEnter: false,
    useClipboard: true,
    icon: action.icon || '',
    imagePath: '',
    path: '',
    hotkey: '',
    url: ''
  };

  renderDeckGrid();
  selectKey(slot);
  syncKeyToHardware(slot, profile.keys[slot]);
}

// Cria uma pasta / sub-página para um slot
async function createFolderForSlot(slot) {
  const defaultName = 'UTILITÁRIOS';
  const folderName = prompt('Digite o nome da pasta:', defaultName) || defaultName;
  const parentPage = state.activeProfile;
  const keySlot1Indexed = slot + 1;

  try {
    const res = await fetch('/api/folder/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        parent_page: parentPage,
        slot: keySlot1Indexed,
        name: folderName
      })
    });
    const data = await res.json();
    if (data.success && data.folder_id) {
      if (!state.profiles[parentPage]) state.profiles[parentPage] = { keys: {} };
      if (!state.profiles[parentPage].keys) state.profiles[parentPage].keys = {};

      state.profiles[parentPage].keys[slot] = {
        title: folderName.toUpperCase(),
        subtitle: 'PASTA',
        bg: '#18181b',
        textColor: '#ffffff',
        accent: '#f59e0b',
        fontSize: '12px',
        icon: 'folder',
        actionType: 'folder',
        actionUuid: 'com.hotspot.streamdock.profile.openchild',
        target: data.folder_id,
        folderId: data.folder_id
      };

      state.profiles[data.folder_id] = {
        id: data.folder_id,
        name: folderName,
        isFolder: true,
        parentPage: parentPage,
        parentSlot: slot,
        keys: {
          0: {
            title: 'VOLTAR',
            subtitle: 'Anterior',
            bg: '#18181b',
            textColor: '#ffffff',
            accent: '#007aff',
            fontSize: '12px',
            icon: 'arrow-left',
            actionType: 'backtoparent',
            actionUuid: 'com.hotspot.streamdock.profile.backtoparent',
            target: parentPage
          }
        }
      };

      renderDeckGrid();
      selectKey(slot);
      showToast(`✓ Pasta "${folderName}" criada! Duplo-clique para entrar.`);
    }
  } catch (err) {
    console.error('Erro ao criar pasta:', err);
  }
}

// Navega para dentro de uma pasta
function openFolder(folderId) {
  if (!folderId || !state.profiles[folderId]) {
    showToast('Pasta não encontrada.');
    return;
  }
  switchProfile(folderId);
}

// Retorna para o nível pai da pasta atual
function goBackParent() {
  const current = state.profiles[state.activeProfile];
  const parentId = current?.parentPage || 'principal';
  switchProfile(parentId);
}

// Renderiza o pipeline de etapas da Multi-Ação
function renderMultiSteps(keyData) {
  const container = document.getElementById('multiStepsContainer');
  if (!container) return;
  container.innerHTML = '';

  if (!keyData.steps) keyData.steps = [];

  if (keyData.steps.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); font-size: 11px; padding: 16px 8px;">
        Nenhuma etapa configurada.<br>
        Clique em <b>"+ Adicionar Ação"</b> ou arraste ações do catálogo para cá.
      </div>
    `;
    return;
  }

  keyData.steps.forEach((step, idx) => {
    const card = document.createElement('div');
    card.className = 'multi-step-card';

    // Badge de índice
    const badge = document.createElement('span');
    badge.className = 'multi-step-badge';
    badge.innerText = `#${idx + 1}`;
    card.appendChild(badge);

    // Tipo de ação
    const typeLabel = document.createElement('span');
    typeLabel.className = 'multi-step-type';
    typeLabel.innerText = getStepTypeName(step);
    card.appendChild(typeLabel);

    // Input configurador específico do tipo
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'multi-step-input';
    input.placeholder = getStepPlaceholder(step);
    input.value = getStepInputValue(step);

    input.oninput = (e) => {
      setStepInputValue(step, e.target.value);
      syncKeyToHardware(state.selectedSlot, keyData);
    };
    card.appendChild(input);

    // Ações de ordenação e exclusão
    const tools = document.createElement('div');
    tools.className = 'multi-step-actions';

    if (idx > 0) {
      const btnUp = document.createElement('button');
      btnUp.className = 'step-tool-btn';
      btnUp.title = 'Mover para cima';
      btnUp.innerText = '▲';
      btnUp.onclick = () => {
        const tmp = keyData.steps[idx - 1];
        keyData.steps[idx - 1] = keyData.steps[idx];
        keyData.steps[idx] = tmp;
        renderMultiSteps(keyData);
        syncKeyToHardware(state.selectedSlot, keyData);
      };
      tools.appendChild(btnUp);
    }

    if (idx < keyData.steps.length - 1) {
      const btnDown = document.createElement('button');
      btnDown.className = 'step-tool-btn';
      btnDown.title = 'Mover para baixo';
      btnDown.innerText = '▼';
      btnDown.onclick = () => {
        const tmp = keyData.steps[idx + 1];
        keyData.steps[idx + 1] = keyData.steps[idx];
        keyData.steps[idx] = tmp;
        renderMultiSteps(keyData);
        syncKeyToHardware(state.selectedSlot, keyData);
      };
      tools.appendChild(btnDown);
    }

    const btnDel = document.createElement('button');
    btnDel.className = 'step-tool-btn danger';
    btnDel.title = 'Remover etapa';
    btnDel.innerText = '✕';
    btnDel.onclick = () => {
      keyData.steps.splice(idx, 1);
      renderMultiSteps(keyData);
      syncKeyToHardware(state.selectedSlot, keyData);
      showToast('Etapa removida da macro.');
    };
    tools.appendChild(btnDel);

    card.appendChild(tools);
    container.appendChild(card);
  });
}

function getStepTypeName(step) {
  const t = (step.type || step.uuid || '').toLowerCase();
  if (t.includes('delay')) return 'Atraso';
  if (t.includes('open')) return 'Abrir App';
  if (t.includes('website') || t.includes('url')) return 'Abrir URL';
  if (t.includes('text')) return 'Digitar Texto';
  if (t.includes('hotkey')) return 'Atalho';
  if (t.includes('multimedia')) return 'Multimídia';
  return 'Ação';
}

function getStepPlaceholder(step) {
  const t = (step.type || step.uuid || '').toLowerCase();
  if (t.includes('delay')) return 'Milissegundos (ex: 500)';
  if (t.includes('open')) return 'Caminho do App (ex: /Applications/Safari.app)';
  if (t.includes('website') || t.includes('url')) return 'https://exemplo.com';
  if (t.includes('text')) return 'Texto a ser digitado ou colado';
  if (t.includes('hotkey')) return 'Atalho (ex: CMD+SHIFT+4)';
  if (t.includes('multimedia')) return 'play / next / prev / mute';
  return 'Parâmetro da ação';
}

function getStepInputValue(step) {
  const t = (step.type || step.uuid || '').toLowerCase();
  if (t.includes('delay')) return step.delay !== undefined ? step.delay : 500;
  if (t.includes('open')) return step.target || step.path || '';
  if (t.includes('website') || t.includes('url')) return step.url || step.target || '';
  if (t.includes('text')) return step.text || '';
  if (t.includes('hotkey')) return step.keys || '';
  if (t.includes('multimedia')) return step.action || 'play';
  return step.target || '';
}

function setStepInputValue(step, val) {
  const t = (step.type || step.uuid || '').toLowerCase();
  if (t.includes('delay')) step.delay = parseInt(val) || 0;
  else if (t.includes('open')) { step.target = val; step.path = val; }
  else if (t.includes('website') || t.includes('url')) { step.url = val; step.target = val; }
  else if (t.includes('text')) step.text = val;
  else if (t.includes('hotkey')) step.keys = val;
  else if (t.includes('multimedia')) step.action = val;
  else step.target = val;
}

function addStepToCurrentMultiAction(actionData) {
  const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
  if (!keyData || keyData.actionType !== 'multiaction') return;
  if (!keyData.steps) keyData.steps = [];

  const uuid = (actionData.uuid || '').toLowerCase();
  let newStep = { type: 'text', text: 'Novo Comando' };

  if (uuid.includes('delay') || actionData.type === 'delay') {
    newStep = { type: 'delay', delay: 500 };
  } else if (uuid.includes('open') || actionData.type === 'open') {
    newStep = { type: 'open', target: actionData.path || '/Applications/Safari.app', delay: 200 };
  } else if (uuid.includes('website') || uuid.includes('url') || actionData.type === 'url') {
    newStep = { type: 'website', target: 'https://', delay: 200 };
  } else if (uuid.includes('hotkey') || actionData.type === 'hotkey') {
    newStep = { type: 'hotkey', keys: 'CMD+C', delay: 150 };
  } else if (uuid.includes('text') || actionData.type === 'text') {
    newStep = { type: 'text', text: '', enter: false };
  } else if (uuid.includes('multimedia') || actionData.type === 'multimedia') {
    newStep = { type: 'multimedia_play' };
  }

  keyData.steps.push(newStep);
  renderMultiSteps(keyData);
  syncKeyToHardware(state.selectedSlot, keyData);
  showToast(`✓ Etapa "${getStepTypeName(newStep)}" adicionada à macro`);
}

function getActionTypeFromUuid(uuid) {
  if (!uuid) return 'text';
  if (uuid.includes('obsstudio') || uuid.startsWith('obs_')) return 'obs';
  if (uuid.includes('routine') || uuid.includes('multiaction') || uuid.includes('macro')) return 'multiaction';
  if (uuid.includes('openchild') || uuid.includes('folder')) return 'folder';
  if (uuid.includes('backtoparent')) return 'backtoparent';
  if (uuid.includes('soundboard') || uuid.includes('playaudio') || uuid.includes('stopaudioplay')) return 'soundboard';
  if (uuid.includes('shell') || uuid.includes('terminal')) return 'shell';
  if (uuid.includes('toggle') || uuid.includes('hotkeyswitch')) return 'toggle';
  if (uuid.includes('closewindow')) return 'close_window';
  if (uuid.includes('closeapp')) return 'close_app';
  if (uuid.includes('minimizewindow')) return 'minimize_window';
  if (uuid.includes('fullscreentoggle')) return 'fullscreen_toggle';
  if (uuid.includes('screenlock')) return 'lock_screen';
  if (uuid.includes('showdesktop')) return 'show_desktop';
  if (uuid.includes('text')) return 'text';
  if (uuid.includes('open')) return 'open';
  if (uuid.includes('hotkey')) return 'hotkey';
  if (uuid.includes('website')) return 'url';
  return 'action';
}

function updateCharCounter(len) {
  const counter = document.getElementById('charCounter');
  if (counter) counter.innerText = `${len} / 5000`;
}

// Eventos e Interações
function bindEvents() {
  // Input de Título
  const inputTitle = document.getElementById('inputKeyTitle');
  let titleDebounceTimer = null;
  if (inputTitle) {
    inputTitle.addEventListener('input', (e) => {
      const val = e.target.value;
      if (!state.profiles[state.activeProfile]) return;
      if (!state.profiles[state.activeProfile].keys) state.profiles[state.activeProfile].keys = {};
      let keyData = state.profiles[state.activeProfile].keys[state.selectedSlot];
      if (!keyData) {
        keyData = { title: '', subtitle: '', bg: '#18181b', textColor: '#ffffff', fontSize: 12, showTitle: true, actionType: 'none' };
        state.profiles[state.activeProfile].keys[state.selectedSlot] = keyData;
      }
      keyData.title = val;
      const targetFolderId = keyData.target || keyData.folderId;
      if (targetFolderId && state.profiles[targetFolderId]) {
        state.profiles[targetFolderId].name = val;
      }

      // Atualiza visual imediatamente no grid e no preview (0ms)
      updateSlotVisual(state.selectedSlot, keyData);

      clearTimeout(titleDebounceTimer);
      titleDebounceTimer = setTimeout(() => {
        syncKeyToHardware(state.selectedSlot, keyData);
      }, 120);
    });
  }

  // Input de Subtítulo (idêntico ao hardware físico)
  const inputSubtitle = document.getElementById('inputKeySubtitle');
  let subDebounceTimer = null;
  if (inputSubtitle) {
    inputSubtitle.addEventListener('input', (e) => {
      const val = e.target.value;
      if (!state.profiles[state.activeProfile]) return;
      if (!state.profiles[state.activeProfile].keys) state.profiles[state.activeProfile].keys = {};
      let keyData = state.profiles[state.activeProfile].keys[state.selectedSlot];
      if (!keyData) {
        keyData = { title: '', subtitle: '', bg: '#18181b', textColor: '#ffffff', fontSize: 12, showTitle: true, actionType: 'none' };
        state.profiles[state.activeProfile].keys[state.selectedSlot] = keyData;
      }
      keyData.subtitle = val;

      // Atualiza visual imediatamente no grid e no preview (0ms)
      updateSlotVisual(state.selectedSlot, keyData);

      clearTimeout(subDebounceTimer);
      subDebounceTimer = setTimeout(() => {
        syncKeyToHardware(state.selectedSlot, keyData);
      }, 120);
    });
  }


  // Textarea de Texto
  let textDebounceTimer = null;
  const txtPayload = document.getElementById('inputTextPayload');
  if (txtPayload) {
    txtPayload.addEventListener('input', (e) => {
      const val = e.target.value;
      updateCharCounter(val.length);
      if (!state.profiles[state.activeProfile]) return;
      if (!state.profiles[state.activeProfile].keys) state.profiles[state.activeProfile].keys = {};
      let keyData = state.profiles[state.activeProfile].keys[state.selectedSlot];
      if (!keyData) {
        keyData = { title: 'Texto', subtitle: '', bg: '#18181b', textColor: '#ffffff', fontSize: 12, showTitle: true, actionType: 'text' };
        state.profiles[state.activeProfile].keys[state.selectedSlot] = keyData;
      }
      keyData.textPayload = val;
      keyData.actionType = 'text';
      updateSlotVisual(state.selectedSlot, keyData);

      clearTimeout(textDebounceTimer);
      textDebounceTimer = setTimeout(() => {
        syncKeyToHardware(state.selectedSlot, keyData);
      }, 70);
    });
  }

  // Checkboxes
  const chkEnter = document.getElementById('chkPressEnter');
  if (chkEnter) {
    chkEnter.addEventListener('change', (e) => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData) {
        keyData.pressEnter = e.target.checked;
        syncKeyToHardware(state.selectedSlot, keyData);
      }
    });
  }

  const chkClip = document.getElementById('chkUseClipboard');
  if (chkClip) {
    chkClip.addEventListener('change', (e) => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData) {
        keyData.useClipboard = e.target.checked;
        syncKeyToHardware(state.selectedSlot, keyData);
      }
    });
  }

  // Caminho da Aplicação (Abre)
  const inputOpen = document.getElementById('inputOpenPath');
  if (inputOpen) {
    inputOpen.addEventListener('input', (e) => {
      if (!state.profiles[state.activeProfile]) return;
      if (!state.profiles[state.activeProfile].keys) state.profiles[state.activeProfile].keys = {};
      let keyData = state.profiles[state.activeProfile].keys[state.selectedSlot];
      if (!keyData) {
        keyData = { title: 'Abre', subtitle: '', bg: '#18181b', textColor: '#ffffff', fontSize: 12, showTitle: true, actionType: 'open' };
        state.profiles[state.activeProfile].keys[state.selectedSlot] = keyData;
      }
      keyData.path = e.target.value;
      keyData.actionType = 'open';
      keyData.uuid = 'com.hotspot.streamdock.system.open';
      updateSlotVisual(state.selectedSlot, keyData);
      syncKeyToHardware(state.selectedSlot, keyData);
    });
  }

  // Seletor Visual de Aplicativos Instalados no Mac (modalAppPicker)
  const btnBrowse = document.getElementById('btnBrowseFile');
  const modalAppPicker = document.getElementById('modalAppPicker');
  const btnCloseAppPicker = document.getElementById('btnCloseAppPicker');
  const searchAppPicker = document.getElementById('searchAppPicker');
  const appPickerGrid = document.getElementById('appPickerGrid');
  const appPickerCount = document.getElementById('appPickerCount');
  let installedAppsCache = null;

  async function openAppPickerModal() {
    if (!modalAppPicker) return;
    modalAppPicker.style.display = 'flex';
    if (searchAppPicker) {
      searchAppPicker.value = '';
      searchAppPicker.focus();
    }

    if (!installedAppsCache) {
      if (appPickerGrid) appPickerGrid.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:20px;">Carregando aplicativos do sistema...</div>';
      try {
        const res = await fetch('/api/browse_app');
        if (res.ok) {
          installedAppsCache = await res.json();
        } else {
          installedAppsCache = [];
        }
      } catch (err) {
        console.warn('Erro ao carregar aplicativos:', err);
        installedAppsCache = [];
      }
    }
    renderAppPickerList('');
  }

  function renderAppPickerList(filter) {
    if (!appPickerGrid) return;
    const q = (filter || '').toLowerCase().trim();
    const list = (installedAppsCache || []).filter(a => !q || a.name.toLowerCase().includes(q) || a.path.toLowerCase().includes(q));

    if (appPickerCount) {
      appPickerCount.innerText = `${list.length} de ${installedAppsCache ? installedAppsCache.length : 0} aplicativos encontrados`;
    }

    if (list.length === 0) {
      appPickerGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); font-size: 12px; padding: 30px;">Nenhum aplicativo encontrado para esta busca.</div>';
      return;
    }

    appPickerGrid.innerHTML = '';
    list.forEach(app => {
      const card = document.createElement('div');
      card.className = 'app-picker-card';
      card.title = app.path;
      card.innerHTML = `
        <div class="app-picker-icon-box">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>
        </div>
        <div class="app-picker-info">
          <span class="app-picker-name">${app.name}</span>
          <span class="app-picker-path">${app.path}</span>
        </div>
      `;
      card.onclick = () => {
        if (!state.profiles[state.activeProfile]) return;
        if (!state.profiles[state.activeProfile].keys) state.profiles[state.activeProfile].keys = {};
        let keyData = state.profiles[state.activeProfile].keys[state.selectedSlot];
        if (!keyData) {
          keyData = { title: app.name, subtitle: '', bg: '#18181b', textColor: '#ffffff', fontSize: 12, showTitle: true, actionType: 'open' };
          state.profiles[state.activeProfile].keys[state.selectedSlot] = keyData;
        }
        keyData.path = app.path;
        keyData.actionType = 'open';
        keyData.uuid = 'com.hotspot.streamdock.system.open';
        if (!keyData.title || keyData.title === 'Nova Ação' || keyData.title === 'Abre' || keyData.title === 'Abra uma aplicação') {
          keyData.title = app.name;
          if (inputTitle) inputTitle.value = app.name;
        }
        if (inputOpen) inputOpen.value = app.path;
        updateSlotVisual(state.selectedSlot, keyData);
        syncKeyToHardware(state.selectedSlot, keyData);
        showToast(`✓ Aplicação vinculada: ${app.name}`);
        modalAppPicker.style.display = 'none';
      };
      appPickerGrid.appendChild(card);
    });
  }

  if (btnBrowse) {
    btnBrowse.onclick = (e) => {
      e.preventDefault();
      openAppPickerModal();
    };
  }

  if (btnCloseAppPicker && modalAppPicker) {
    btnCloseAppPicker.onclick = () => modalAppPicker.style.display = 'none';
    modalAppPicker.onclick = (e) => {
      if (e.target === modalAppPicker) modalAppPicker.style.display = 'none';
    };
  }

  if (searchAppPicker) {
    searchAppPicker.addEventListener('input', (e) => {
      renderAppPickerList(e.target.value);
    });
  }

  // Botões de Teste Instantâneo de Ações no macOS
  const btnTestCurrent = document.getElementById('btnTestCurrentAction');
  if (btnTestCurrent) {
    btnTestCurrent.onclick = async () => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (!keyData) {
        showToast('Nenhuma ação configurada nesta tecla para testar.');
        return;
      }
      const act = buildActionPayload(keyData);
      triggerKeyAnimation(state.selectedSlot);
      try {
        await fetch('/api/key/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: act, slot: state.selectedSlot + 1, page: state.activeProfile })
        });
        showToast(`▶ Executando "${keyData.title || 'Ação'}" no macOS...`);
      } catch (e) {
        showToast('Erro ao disparar teste no Mac');
      }
    };
  }

  const btnTestOpen = document.getElementById('btnTestOpenAction');
  if (btnTestOpen) {
    btnTestOpen.onclick = async () => {
      const pathVal = inputOpen ? inputOpen.value.trim() : '';
      if (!pathVal) {
        showToast('Preencha o app ou arquivo antes de testar.');
        return;
      }
      try {
        await fetch('/api/key/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: { type: 'open', target: pathVal, path: pathVal } })
        });
        showToast(`▶ Abrindo "${pathVal}" no Mac...`);
      } catch (e) {
        showToast('Erro ao abrir app no Mac');
      }
    };
  }

  const btnTestHotkey = document.getElementById('btnTestHotkeyAction');
  if (btnTestHotkey) {
    btnTestHotkey.onclick = async () => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      const hotkeyVal = keyData?.hotkey || badgeHotkey?.innerText;
      if (!hotkeyVal || hotkeyVal.includes('Pressione')) {
        showToast('Grave um atalho antes de testar.');
        return;
      }
      try {
        await fetch('/api/key/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: { type: 'hotkey', keys: hotkeyVal } })
        });
        showToast(`▶ Enviando atalho "${hotkeyVal}"...`);
      } catch (e) {
        showToast('Erro ao disparar atalho no Mac');
      }
    };
  }

  const btnTestUrl = document.getElementById('btnTestUrlAction');
  if (btnTestUrl) {
    btnTestUrl.onclick = async () => {
      const urlInput = document.getElementById('inputUrlTarget');
      const urlVal = urlInput ? urlInput.value.trim() : '';
      if (!urlVal) {
        showToast('Preencha a URL antes de testar.');
        return;
      }
      try {
        await fetch('/api/key/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: { type: 'website', target: urlVal } })
        });
        showToast(`▶ Abrindo website "${urlVal}"...`);
      } catch (e) {
        showToast('Erro ao abrir site');
      }
    };
  }

  // Gravador de Atalho (Hotkey)
  const btnRecord = document.getElementById('btnRecordHotkey');
  const badgeHotkey = document.getElementById('hotkeyBadge');
  if (btnRecord && badgeHotkey) {
    let isRecording = false;
    let recordListener = null;

    btnRecord.onclick = () => {
      if (isRecording) {
        isRecording = false;
        btnRecord.classList.remove('record-active');
        btnRecord.innerText = 'Gravar Atalho';
        if (recordListener) window.removeEventListener('keydown', recordListener, true);
        return;
      }

      isRecording = true;
      btnRecord.classList.add('record-active');
      btnRecord.innerText = 'Gravando...';
      badgeHotkey.innerText = 'Pressione as teclas...';

      recordListener = (e) => {
        e.preventDefault();
        e.stopPropagation();

        const parts = [];
        if (e.metaKey) parts.push('Cmd');
        if (e.ctrlKey) parts.push('Ctrl');
        if (e.altKey) parts.push('Alt');
        if (e.shiftKey) parts.push('Shift');

        const key = e.key.toUpperCase();
        if (['META', 'CONTROL', 'ALT', 'SHIFT'].includes(key)) {
          badgeHotkey.innerText = parts.join(' + ') + ' + ...';
          return;
        }

        parts.push(key);
        const combo = parts.join(' + ');
        badgeHotkey.innerText = combo;

        isRecording = false;
        btnRecord.classList.remove('record-active');
        btnRecord.innerText = 'Gravar Atalho';
        window.removeEventListener('keydown', recordListener, true);

        if (!state.profiles[state.activeProfile]) return;
        if (!state.profiles[state.activeProfile].keys) state.profiles[state.activeProfile].keys = {};
        let keyData = state.profiles[state.activeProfile].keys[state.selectedSlot];
        if (!keyData) {
          keyData = { title: combo, subtitle: 'Atalho', bg: '#18181b', textColor: '#ffffff', fontSize: 12, showTitle: true, actionType: 'hotkey' };
          state.profiles[state.activeProfile].keys[state.selectedSlot] = keyData;
        }
        keyData.hotkey = combo;
        keyData.actionType = 'hotkey';
        keyData.uuid = 'com.hotspot.streamdock.system.hotkey';
        updateSlotVisual(state.selectedSlot, keyData);
        syncKeyToHardware(state.selectedSlot, keyData);
        showToast(`✓ Atalho gravado: ${combo}`);
      };

      window.addEventListener('keydown', recordListener, true);
    };
  }

  // URL Target
  const inputUrl = document.getElementById('inputUrlTarget');
  if (inputUrl) {
    inputUrl.addEventListener('input', (e) => {
      if (!state.profiles[state.activeProfile]) return;
      if (!state.profiles[state.activeProfile].keys) state.profiles[state.activeProfile].keys = {};
      let keyData = state.profiles[state.activeProfile].keys[state.selectedSlot];
      if (!keyData) {
        keyData = { title: 'Site', subtitle: '', bg: '#18181b', textColor: '#ffffff', fontSize: 12, showTitle: true, actionType: 'url' };
        state.profiles[state.activeProfile].keys[state.selectedSlot] = keyData;
      }
      keyData.url = e.target.value;
      keyData.actionType = 'url';
      keyData.uuid = 'com.hotspot.streamdock.system.website';
      updateSlotVisual(state.selectedSlot, keyData);
      syncKeyToHardware(state.selectedSlot, keyData);
    });
  }

  // Soundboard (Áudio)
  const inputSound = document.getElementById('inputSoundboardPath');
  const btnBrowseSound = document.getElementById('btnBrowseSound');
  const btnTestSound = document.getElementById('btnTestSound');

  if (inputSound) {
    inputSound.addEventListener('input', (e) => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData) {
        keyData.path = e.target.value;
        keyData.target = e.target.value;
        syncKeyToHardware(state.selectedSlot, keyData);
      }
    });
  }

  if (btnBrowseSound) {
    btnBrowseSound.onclick = () => {
      const audioInput = document.createElement('input');
      audioInput.type = 'file';
      audioInput.accept = '.mp3,.wav,.m4a,.ogg,.aac';
      audioInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
          const path = file.path || `/Users/hugosilva/Music/${file.name}`;
          if (inputSound) inputSound.value = path;
          const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
          if (keyData) {
            keyData.path = path;
            keyData.target = path;
            if (!keyData.title || keyData.title === 'TOCAR SOM') {
              keyData.title = file.name.split('.')[0].toUpperCase().slice(0, 10);
              const inpTitle = document.getElementById('inputKeyTitle');
              if (inpTitle) inpTitle.value = keyData.title;
              const lbl = document.getElementById('previewKeyLabel');
              if (lbl) lbl.innerText = keyData.title;
            }
            renderDeckGrid();
            syncKeyToHardware(state.selectedSlot, keyData);
            showToast(`✓ Áudio associado: ${file.name}`);
          }
        }
      };
      audioInput.click();
    };
  }

  if (btnTestSound) {
    btnTestSound.onclick = () => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData && (keyData.path || keyData.target)) {
        showToast('▶ Reproduzindo som no Mac...');
        fetch('/api/key/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: { type: 'soundboard', path: keyData.path || keyData.target } })
        });
      } else {
        showToast('Selecione um arquivo de som primeiro.');
      }
    };
  }

  // Comando Shell / Terminal
  const inputShell = document.getElementById('inputShellCommand');
  const btnTestShell = document.getElementById('btnTestShellCommand');

  if (inputShell) {
    inputShell.addEventListener('input', (e) => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData) {
        keyData.command = e.target.value;
        keyData.target = e.target.value;
        syncKeyToHardware(state.selectedSlot, keyData);
      }
    });
  }

  if (btnTestShell) {
    btnTestShell.onclick = () => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData && (keyData.command || keyData.target)) {
        showToast('⚡ Executando comando shell...');
        fetch('/api/key/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: { type: 'shell_command', command: keyData.command || keyData.target } })
        });
      } else {
        showToast('Digite um comando primeiro.');
      }
    };
  }

  // Toggle A/B
  const tA = document.getElementById('inputToggleTitleA');
  const kA = document.getElementById('inputToggleKeysA');
  const tB = document.getElementById('inputToggleTitleB');
  const kB = document.getElementById('inputToggleKeysB');

  [tA, kA, tB, kB].forEach(el => {
    if (el) {
      el.addEventListener('input', () => {
        const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
        if (keyData) {
          if (tA) keyData.title_a = tA.value;
          if (kA) keyData.keys_a = kA.value;
          if (tB) keyData.title_b = tB.value;
          if (kB) keyData.keys_b = kB.value;
          syncKeyToHardware(state.selectedSlot, keyData);
        }
      });
    }
  });

  // Alternar Menu de Adição de Etapas da Multi-Ação
  const btnToggleMulti = document.getElementById('btnToggleAddMultiMenu');
  const multiMenu = document.getElementById('multiAddMenu');
  if (btnToggleMulti && multiMenu) {
    btnToggleMulti.onclick = () => {
      const isHidden = multiMenu.style.display === 'none';
      multiMenu.style.display = isHidden ? 'flex' : 'none';
    };
  }

  // Cliques nas opções de adição de etapa
  document.querySelectorAll('.add-step-opt-btn').forEach(btn => {
    btn.onclick = () => {
      const stepType = btn.dataset.type;
      addStepToCurrentMultiAction({ type: stepType });
      if (multiMenu) multiMenu.style.display = 'none';
    };
  });

  // Drop target para adicionar ações diretamente no container de etapas
  const multiContainer = document.getElementById('multiStepsContainer');
  if (multiContainer) {
    multiContainer.ondragover = (e) => {
      e.preventDefault();
      multiContainer.classList.add('drag-over');
    };
    multiContainer.ondragleave = () => {
      multiContainer.classList.remove('drag-over');
    };
    multiContainer.ondrop = (e) => {
      e.preventDefault();
      multiContainer.classList.remove('drag-over');
      const actionDataRaw = e.dataTransfer.getData('application/json');
      if (actionDataRaw) {
        try {
          const actionData = JSON.parse(actionDataRaw);
          addStepToCurrentMultiAction(actionData);
        } catch (err) {}
      }
    };
  }

  // Swatches de Cor da Tecla
  document.querySelectorAll('.swatch:not(.scene-swatch)').forEach(btn => {
    btn.onclick = () => {
      const color = btn.dataset.color;
      applyKeyColor(color);
    };
  });

  // Color picker customizado da Tecla
  const customPicker = document.getElementById('customColorPicker');
  if (customPicker) {
    customPicker.addEventListener('input', (e) => {
      applyKeyColor(e.target.value);
    });
  }

  // Botão Aplicar Cor a Todas as 15 Telas
  const btnApplyAll = document.getElementById('btnApplyColorToAll');
  if (btnApplyAll) {
    btnApplyAll.onclick = () => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      const curColor = keyData?.bg || (document.getElementById('customColorPicker')?.value) || '#18181b';
      applyKeyColor(curColor, true);
    };
  }

  // Swatches de Cor da Cena Inteira (Empty State)
  document.querySelectorAll('.scene-swatch').forEach(btn => {
    btn.onclick = () => {
      const color = btn.dataset.color;
      applySceneColor(color);
    };
  });

  // Color picker customizado da Cena
  const scenePicker = document.getElementById('sceneCustomColorPicker');
  if (scenePicker) {
    scenePicker.addEventListener('input', (e) => {
      applySceneColor(e.target.value);
    });
  }

  // Botão Aplicar Cor da Cena
  const btnApplyScene = document.getElementById('btnApplySceneColor');
  if (btnApplyScene) {
    btnApplyScene.onclick = () => {
      const sc = document.getElementById('sceneCustomColorPicker')?.value || '#18181b';
      applySceneColor(sc);
    };
  }

  // Botão de Lixeira (Excluir Ação da Tecla)
  const btnDelKey = document.getElementById('btnDeleteKeyAction');
  if (btnDelKey) {
    btnDelKey.onclick = () => {
      const profile = state.profiles[state.activeProfile];
      if (profile && profile.keys[state.selectedSlot]) {
        delete profile.keys[state.selectedSlot];
        renderDeckGrid();
        selectKey(state.selectedSlot);
        syncKeyToHardware(state.selectedSlot, null);
      }
    };
  }

  // Drag-and-drop e Clique Direto dos itens da biblioteca de ações
  document.querySelectorAll('.action-item').forEach(item => {
    item.ondragstart = (e) => {
      const uuid = item.dataset.uuid;
      const name = item.dataset.name;
      const category = item.closest('.accordion-item')?.querySelector('.acc-name')?.innerText || 'Geral';
      const icon = item.querySelector('.act-icon')?.src || '';
      e.dataTransfer.setData('application/json', JSON.stringify({ uuid, name, category, icon }));
    };

    // Clique direto: aplica imediatamente a ação ao slot selecionado e abre as Propriedades
    item.onclick = (e) => {
      e.preventDefault();
      const slot = (state.selectedSlot !== null && state.selectedSlot !== undefined) ? state.selectedSlot : 0;
      const uuid = item.dataset.uuid;
      const name = item.dataset.name;
      const category = item.closest('.accordion-item')?.querySelector('.acc-name')?.innerText || 'Geral';
      const icon = item.querySelector('.act-icon')?.src || '';
      assignActionToSlot(slot, { uuid, name, category, icon });
      switchRightTab('tabPaneInspector');
      showToast(`✓ Ação "${name}" aplicada à tecla ${slot + 1}`);
    };
  });

  // Acordeões colapsáveis
  document.querySelectorAll('.accordion-header').forEach(header => {
    header.onclick = () => {
      const parent = header.closest('.accordion-item');
      parent.classList.toggle('open');
    };
  });

  // Busca no catálogo
  const searchInput = document.getElementById('searchCatalog');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().trim();
      document.querySelectorAll('.action-item').forEach(act => {
        const name = (act.dataset.name || '').toLowerCase();
        const match = name.includes(query);
        act.style.display = match ? 'flex' : 'none';
      });
      if (query.length > 0) {
        document.querySelectorAll('.accordion-item').forEach(acc => acc.classList.add('open'));
      }
    });
  }

  // Popover Tipográfico "T"
  const btnTypo = document.getElementById('btnTypography');
  const popoverTypo = document.getElementById('typographyPopover');
  if (btnTypo && popoverTypo) {
    btnTypo.onclick = (e) => {
      e.stopPropagation();
      const isVisible = popoverTypo.style.display === 'flex';
      popoverTypo.style.display = isVisible ? 'none' : 'flex';
    };
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.typography-anchor')) {
        popoverTypo.style.display = 'none';
      }
    });

    // Família da Fonte
    const selFontFamily = document.getElementById('selectFontFamily');
    if (selFontFamily) {
      selFontFamily.onchange = (e) => {
        const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
        if (keyData) {
          keyData.fontFamily = e.target.value;
          renderDeckGrid();
          selectKey(state.selectedSlot);
          syncKeyToHardware(state.selectedSlot, keyData);
        }
      };
    }

    // Estilos Tipográficos: Negrito, Itálico, Sublinhado
    const btnBold = document.getElementById('btnStyleBold');
    if (btnBold) {
      btnBold.onclick = () => {
        const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
        if (keyData) {
          keyData.bold = !keyData.bold;
          btnBold.classList.toggle('active', keyData.bold);
          renderDeckGrid();
          selectKey(state.selectedSlot);
          syncKeyToHardware(state.selectedSlot, keyData);
        }
      };
    }

    const btnItalic = document.getElementById('btnStyleItalic');
    if (btnItalic) {
      btnItalic.onclick = () => {
        const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
        if (keyData) {
          keyData.italic = !keyData.italic;
          btnItalic.classList.toggle('active', keyData.italic);
          renderDeckGrid();
          selectKey(state.selectedSlot);
          syncKeyToHardware(state.selectedSlot, keyData);
        }
      };
    }

    const btnUnderline = document.getElementById('btnStyleUnderline');
    if (btnUnderline) {
      btnUnderline.onclick = () => {
        const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
        if (keyData) {
          keyData.underline = !keyData.underline;
          btnUnderline.classList.toggle('active', keyData.underline);
          renderDeckGrid();
          selectKey(state.selectedSlot);
          syncKeyToHardware(state.selectedSlot, keyData);
        }
      };
    }

    // Alinhamentos Verticais (Topo / Centro / Base)
    ['btnAlignTop', 'btnAlignMiddle', 'btnAlignBottom'].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.onclick = () => {
          document.querySelectorAll('.align-btn-group .pop-btn').forEach(b => b.classList.remove('active'));
          el.classList.add('active');
          const alignMap = { btnAlignTop: 'top', btnAlignMiddle: 'middle', btnAlignBottom: 'bottom' };
          const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
          if (keyData) {
            keyData.titleAlignment = alignMap[id] || 'middle';
            renderDeckGrid();
            selectKey(state.selectedSlot);
            syncKeyToHardware(state.selectedSlot, keyData);
          }
        };
      }
    });

    // Ocultar Título (Modo Ícone Destaque)
    const chkDoNotShow = document.getElementById('chkDoNotShowTitle');
    if (chkDoNotShow) {
      chkDoNotShow.onchange = (e) => {
        const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
        if (keyData) {
          keyData.showTitle = !e.target.checked;
          renderDeckGrid();
          selectKey(state.selectedSlot);
          syncKeyToHardware(state.selectedSlot, keyData);
        }
      };
    }

    // Tamanho da fonte
    const selectSize = document.getElementById('selectFontSize');
    if (selectSize) {
      selectSize.onchange = (e) => {
        const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
        if (keyData) {
          keyData.fontSize = e.target.value + 'px';
          renderDeckGrid();
          selectKey(state.selectedSlot);
          syncKeyToHardware(state.selectedSlot, keyData);
        }
      };
    }
  }

  // Borda LCD: Espessura e Cor
  const selBorderWidth = document.getElementById('selectBorderWidth');
  if (selBorderWidth) {
    selBorderWidth.onchange = (e) => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData) {
        keyData.borderWidth = parseInt(e.target.value) || 0;
        renderDeckGrid();
        selectKey(state.selectedSlot);
        syncKeyToHardware(state.selectedSlot, keyData);
      }
    };
  }

  const inpBorderColor = document.getElementById('inputBorderColor');
  if (inpBorderColor) {
    inpBorderColor.oninput = (e) => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData) {
        keyData.borderColor = e.target.value;
        if (!keyData.borderWidth) keyData.borderWidth = 2;
        if (selBorderWidth && selBorderWidth.value === '0') selBorderWidth.value = '2';
        renderDeckGrid();
        selectKey(state.selectedSlot);
        syncKeyToHardware(state.selectedSlot, keyData);
      }
    };
  }

  // Ajuste de Imagem (Cobrir / Conter)
  const selImageFit = document.getElementById('selectImageFit');
  if (selImageFit) {
    selImageFit.onchange = (e) => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData) {
        keyData.imageFit = e.target.value;
        renderDeckGrid();
        selectKey(state.selectedSlot);
        syncKeyToHardware(state.selectedSlot, keyData);
      }
    };
  }

  // Remover Imagem / Ícone
  const btnRemImg = document.getElementById('btnRemoveKeyImage');
  if (btnRemImg) {
    btnRemImg.onclick = () => {
      const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
      if (keyData) {
        delete keyData.imagePath;
        delete keyData.icon;
        renderDeckGrid();
        selectKey(state.selectedSlot);
        syncKeyToHardware(state.selectedSlot, keyData);
        showToast('Imagem removida da tecla');
      }
    };
  }

  // Carregar Imagem Local para Tecla
  const btnUploadImg = document.getElementById('btnUploadKeyImage');
  const fileKeyImg = document.getElementById('fileInputKeyImage');
  if (btnUploadImg && fileKeyImg) {
    btnUploadImg.onclick = () => fileKeyImg.click();
    fileKeyImg.onchange = (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async () => {
        showToast('Enviando imagem para a tecla...');
        try {
          const res = await fetch('/api/upload_image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: file.name, base64: reader.result })
          });
          const data = await res.json();
          if (data.success && data.path) {
            const keyData = state.profiles[state.activeProfile]?.keys[state.selectedSlot];
            if (keyData) {
              keyData.imagePath = data.path;
              renderDeckGrid();
              selectKey(state.selectedSlot);
              syncKeyToHardware(state.selectedSlot, keyData);
              showToast('✓ Imagem aplicada com sucesso!');
            }
          } else {
            showToast('Erro no envio da imagem: ' + (data.error || ''));
          }
        } catch (err) {
          showToast('Falha na conexão ao enviar imagem');
        }
      };
      reader.readAsDataURL(file);
      fileKeyImg.value = '';
    };
  }

  // Botão Adicionar Cena
  const btnAddScene = document.getElementById('btnAddScene');
  if (btnAddScene) {
    btnAddScene.onclick = async () => {
      const name = prompt('Nome da nova Cena:', 'Nova Cena');
      if (name && name.trim()) {
        const cleanName = name.trim();
        const id = 'cena_' + Date.now();
        showToast(`Criando cena "${cleanName}"...`);

        try {
          const res = await fetch('/api/page/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, name: cleanName })
          });
          if (res.ok) {
            await loadServerState();
            switchProfile(id);
            showToast(`✓ Cena "${cleanName}" criada e ativa!`);
          }
        } catch (err) {
          showToast('Erro ao criar cena no servidor');
          console.error(err);
        }
      }
    };
  }

  // Botão Excluir Cena
  const btnDelScene = document.getElementById('btnDeleteScene');
  if (btnDelScene) {
    btnDelScene.onclick = async () => {
      if (Object.keys(state.profiles).length <= 1) {
        alert('Você precisa manter pelo menos uma cena.');
        return;
      }
      const currentId = state.activeProfile;
      if (currentId === 'principal') {
        alert('A Cena Padrão oficial não pode ser excluída.');
        return;
      }
      const sceneName = state.profiles[currentId]?.name || currentId;
      if (confirm(`Deseja excluir a cena "${sceneName}"?`)) {
        showToast(`Excluindo cena "${sceneName}"...`);
        try {
          await fetch('/api/page/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: currentId })
          });
          await loadServerState();
          const remaining = Object.keys(state.profiles)[0] || 'principal';
          switchProfile(remaining);
          showToast(`✓ Cena excluída`);
        } catch (err) {
          showToast('Erro ao excluir cena no servidor');
          console.error(err);
        }
      }
    };
  }

  // Botão Adicionar Página
  const btnAddPage = document.getElementById('btnAddPage');
  if (btnAddPage) {
    btnAddPage.onclick = async () => {
      const currentName = state.profiles[state.activeProfile]?.name || 'Página';
      const pageName = prompt('Nome da nova sub-página / tela:', `${currentName} - Pág 2`);
      if (pageName && pageName.trim()) {
        const newId = 'page_' + Date.now();
        showToast(`Criando nova página...`);
        try {
          await fetch('/api/page/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: newId, name: pageName.trim() })
          });
          await loadServerState();
          switchProfile(newId);
          showToast(`✓ Página "${pageName.trim()}" criada!`);
        } catch (err) {
          showToast('Erro ao criar página');
        }
      }
    };
  }

  // Botão Conectar Hardware (Status Header)
  const btnConnect = document.getElementById('btnConnectDevice');
  if (btnConnect) {
    btnConnect.onclick = async () => {
      showToast('Conectando ao Stream Deck D6...');
      try {
        const res = await fetch('/api/connect');
        const data = await res.json();
        if (data.connected) {
          showToast('✓ Conectado com sucesso ao Stream Deck D6!');
          await loadServerState();
        } else {
          showToast('Dispositivo não encontrado na porta USB.');
        }
      } catch (e) {
        showToast('Erro de comunicação com o servidor local.');
      }
    };
  }

  // ================= MODAIS & NAVEGAÇÃO =================
  initTheme();
  bindModalEvents();
  setupProfileDropdown(state, loadServerState, switchProfile, openLinkAppModal);
  bindGlobalShortcutsAndContextMenu();
}

// Atalhos globais de teclado (⌘C, ⌘V, ⌘X, ⌘D, ⌫, Setas) e eventos de menu de contexto
function bindGlobalShortcutsAndContextMenu() {
  document.addEventListener('click', (e) => {
    const menu = document.getElementById('slotContextMenu');
    if (menu && !e.target.closest('#slotContextMenu')) {
      menu.style.display = 'none';
    }
  });

  window.addEventListener('keydown', (e) => {
    const tag = document.activeElement?.tagName;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) {
      if (e.key === 'Escape') {
        const menu = document.getElementById('slotContextMenu');
        if (menu) menu.style.display = 'none';
        document.activeElement?.blur();
      }
      return;
    }

    const menu = document.getElementById('slotContextMenu');
    if (e.key === 'Escape' && menu && menu.style.display !== 'none') {
      menu.style.display = 'none';
      return;
    }

    // Copiar (⌘C / Ctrl+C)
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'c') {
      e.preventDefault();
      copyKey(state.selectedSlot);
    }
    // Colar (⌘V / Ctrl+V)
    else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'v') {
      e.preventDefault();
      pasteKey(state.selectedSlot);
    }
    // Recortar (⌘X / Ctrl+X)
    else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'x') {
      e.preventDefault();
      cutKey(state.selectedSlot);
    }
    // Excluir Ação (Backspace ou Delete)
    else if (e.key === 'Backspace' || e.key === 'Delete') {
      e.preventDefault();
      deleteKey(state.selectedSlot);
    }
    // Duplicar Tecla (⌘D)
    else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'd') {
      e.preventDefault();
      duplicateKey(state.selectedSlot);
    }
    // Navegação em Grid 5x3 com Teclas de Seta
    else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      selectKey(Math.max(0, state.selectedSlot - 1));
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      selectKey(Math.min(14, state.selectedSlot + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      selectKey(Math.max(0, state.selectedSlot - 5));
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      selectKey(Math.min(14, state.selectedSlot + 5));
    }
  });
}

// Vincula abertura, abas e ações de todos os painéis e modais
function bindModalEvents() {
  // Vincula cliques nas abas da direita
  document.querySelectorAll('.side-tab-btn').forEach(btn => {
    btn.onclick = () => {
      const tabId = btn.dataset.tab;
      if (tabId) switchRightTab(tabId);
    };
  });

  // Botão de Toggle da barra lateral (mobile/telas menores)
  const btnToggleSide = document.getElementById('btnToggleSideTabs');
  if (btnToggleSide) {
    btnToggleSide.onclick = () => {
      const side = document.getElementById('colSideTabs');
      if (side) {
        const isHidden = window.getComputedStyle(side).display === 'none';
        side.style.display = isHidden ? 'flex' : 'none';
      }
    };
  }

  // Botão Fullscreen
  const btnFullscreen = document.getElementById('btnFullscreenToggle');
  if (btnFullscreen) {
    btnFullscreen.onclick = () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    };
  }

  // Pílula do OBS no Header - Atalho direto para configurações de OBS
  const headerObsPill = document.getElementById('headerObsStatusPill');
  if (headerObsPill) {
    headerObsPill.onclick = () => {
      switchRightTab('tabPaneSettings');
      const obsSubTabBtn = document.querySelector('.modal-tab-btn[data-tab="tabOBS"]');
      if (obsSubTabBtn) obsSubTabBtn.click();
    };
  }

  // Botões de Topo
  const btnSettings = document.getElementById('btnNavSettings');
  if (btnSettings) {
    btnSettings.onclick = () => switchRightTab('tabPaneSettings');
  }

  const btnStore = document.getElementById('btnNavStore');
  if (btnStore) {
    btnStore.onclick = () => switchRightTab('tabPaneStore');
  }

  const btnLayouts = document.getElementById('btnNavLayouts');
  if (btnLayouts) {
    btnLayouts.onclick = () => switchRightTab('tabPaneSkins');
  }

  const btnHelp = document.getElementById('btnNavHelp');
  if (btnHelp) {
    btnHelp.onclick = () => {
      openModal('modalHelp');
    };
  }

  // Fechamento de Modais (botão "x" e clique fora)
  document.querySelectorAll('.modal-close-btn').forEach(btn => {
    btn.onclick = () => {
      const modalId = btn.dataset.close;
      if (modalId) closeModal(modalId);
    };
  });

  document.querySelectorAll('.studio-modal-backdrop').forEach(backdrop => {
    backdrop.onclick = (e) => {
      if (e.target === backdrop) {
        backdrop.style.display = 'none';
      }
    };
  });

  // Sub-abas de Configurações
  document.querySelectorAll('.modal-tab-btn').forEach(tabBtn => {
    tabBtn.onclick = () => {
      const container = tabBtn.closest('.settings-wrapper') || tabBtn.closest('.studio-modal-window') || document;
      container.querySelectorAll('.modal-tab-btn').forEach(b => b.classList.remove('active'));
      container.querySelectorAll('.modal-tab-content').forEach(c => c.classList.remove('active'));

      tabBtn.classList.add('active');
      const targetId = tabBtn.dataset.tab;
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add('active');
    };
  });

  // Slider de Brilho
  const sliderBright = document.getElementById('settingBrightnessSlider');
  const valBright = document.getElementById('settingBrightnessVal');
  if (sliderBright && valBright) {
    let brightTimer = null;
    sliderBright.oninput = (e) => {
      const val = e.target.value;
      valBright.innerText = `${val}%`;
      clearTimeout(brightTimer);
      brightTimer = setTimeout(async () => {
        try {
          await fetch('/api/brightness', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ percent: parseInt(val) })
          });
          showToast(`✓ Brilho ajustado para ${val}%`);
        } catch (err) {
          console.warn('Erro ao ajustar brilho:', err);
        }
      }, 150);
    };
  }

  // Rotação / Orientação
  const selRot = document.getElementById('settingRotationSelect');
  if (selRot) {
    selRot.onchange = async (e) => {
      const rot = parseInt(e.target.value);
      try {
        await fetch('/api/rotation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rotation: rot })
        });
        showToast(`✓ Orientação alterada para ${rot}°`);
      } catch (err) {
        showToast('Erro ao atualizar rotação no servidor');
      }
    };
  }

  // Desligar tela (Screen Off)
  const selScreenOff = document.getElementById('settingScreenOffSelect');
  if (selScreenOff) {
    selScreenOff.onchange = async (e) => {
      const sec = parseInt(e.target.value);
      try {
        await fetch('/api/screen_off', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ seconds: sec })
        });
        showToast('✓ Tempo de inatividade atualizado');
      } catch (err) {
        console.warn('Erro ao atualizar timer de tela:', err);
      }
    };
  }

  // LED Seguir o modo de suspensão do macOS (LED Sleep Follow)
  const chkLedFollow = document.getElementById('settingLedSleepFollowCheck');
  if (chkLedFollow) {
    chkLedFollow.onchange = async () => {
      const enabled = chkLedFollow.checked;
      state.ledSleepFollow = enabled;
      try {
        await fetch('/api/settings/led_sleep_follow', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled })
        });
        showToast(enabled ? '✓ LED seguir suspensão ativado' : 'LED seguir suspensão desativado');
      } catch (err) {
        console.warn('Erro ao salvar led_sleep_follow:', err);
      }
    };
  }

  // Restaurar Backup Dourado
  const btnRestoreGolden = document.getElementById('btnRestoreGoldenBackup');
  if (btnRestoreGolden) {
    btnRestoreGolden.onclick = async () => {
      if (confirm('Deseja restaurar todos os perfis e ações protegidos pelo Guardian? Isso sobrescreverá alterações locais não salvas.')) {
        showToast('Restaurando backup oficial...');
        try {
          const res = await fetch('/api/backup/restore_golden', { method: 'POST' });
          const data = await res.json();
          if (data.success) {
            await loadServerState();
            showToast('✓ Backup dourado restaurado com sucesso!');
          } else {
            showToast('Nenhum backup encontrado no disco.');
          }
        } catch (err) {
          showToast('Erro ao restaurar backup oficial.');
        }
      }
    };
  }

  // Exportar Backup Completo
  const btnExport = document.getElementById('btnExportFullConfig');
  if (btnExport) {
    btnExport.onclick = () => {
      window.location.href = '/api/backup/export';
      showToast('✓ Arquivo de backup transferido');
    };
  }

  // Restaurar Backup Completo
  const btnImportBackup = document.getElementById('btnImportFullConfig');
  const fileInputBackup = document.getElementById('fileInputFullBackup');
  if (btnImportBackup && fileInputBackup) {
    btnImportBackup.onclick = () => fileInputBackup.click();
    fileInputBackup.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = async (evt) => {
          try {
            const json = JSON.parse(evt.target.result);
            if (json && json.pages) {
              showToast('Restaurando configuração completa...');
              const res = await fetch('/api/backup/import_full', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: json })
              });
              const resData = await res.json();
              if (resData.success) {
                await loadServerState();
                showToast(`✓ Backup restaurado com ${resData.pages_count} cenas!`);
              } else {
                showToast('Erro ao importar backup: arquivo inválido');
              }
            } else {
              showToast('Arquivo de backup inválido (pages não encontrado)');
            }
          } catch (err) {
            showToast('Erro ao ler arquivo JSON de backup');
            console.error(err);
          }
        };
        reader.readAsText(file);
      }
    };
  }

  // Auto-Switch de Perfil por App Ativo
  const chkAutoSwitch = document.getElementById('settingAutoSwitchCheck');
  if (chkAutoSwitch) {
    chkAutoSwitch.checked = state.autoSwitchEnabled !== false;
    chkAutoSwitch.onchange = async () => {
      const isEnabled = chkAutoSwitch.checked;
      state.autoSwitchEnabled = isEnabled;
      updateSceneInspector();
      try {
        await fetch('/api/autoswitch/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled: isEnabled })
        });
        showToast(isEnabled ? '✓ Auto-Switch de perfil ativado' : 'Auto-Switch de perfil desativado');
      } catch (e) {
        console.error(e);
      }
    };
  }

  // Botão Vincular App no Inspector de Cena
  const btnInspLink = document.getElementById('btnInspectorLinkApp');
  if (btnInspLink) {
    btnInspLink.onclick = () => openLinkAppModal(state.activeProfile);
  }

  // Botão Suspender Agora (modal de configurações)
  const btnTestSleep = document.getElementById('btnTestSleepNow');
  if (btnTestSleep) {
    btnTestSleep.onclick = async () => {
      closeModal('modalSettings');
      showToast('Colocando Stream Deck em repouso (Sleep)...');
      try {
        await fetch('/api/device/sleep', { method: 'POST' });
        await loadServerState();
      } catch (e) {
        console.error(e);
      }
    };
  }

  // Botão Nav Sleep (Top Bar)
  const btnNavSleep = document.getElementById('btnNavSleep');
  if (btnNavSleep) {
    btnNavSleep.onclick = async () => {
      const endpoint = state.isAsleep ? '/api/device/wake' : '/api/device/sleep';
      showToast(state.isAsleep ? 'Acordando Stream Deck...' : 'Colocando em repouso (Sleep)...');
      try {
        await fetch(endpoint, { method: 'POST' });
        await loadServerState();
      } catch (e) {
        console.error(e);
      }
    };
  }
}

function openModal(id) {
  if (id === 'modalSettings') {
    switchRightTab('tabPaneSettings');
    return;
  }
  if (id === 'modalStore') {
    switchRightTab('tabPaneStore');
    return;
  }
  if (id === 'modalLayouts') {
    switchRightTab('tabPaneSkins');
    return;
  }
  const el = document.getElementById(id);
  if (el) el.style.display = 'flex';
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

function initModals() {
  // Handler global para botões data-close em qualquer modal
  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.onclick = () => {
      const targetId = btn.getAttribute('data-close');
      const el = document.getElementById(targetId);
      if (el) el.style.display = 'none';
    };
  });
}

// Abre o Modal de Vinculação de Aplicativo (Auto-Switch)
async function openLinkAppModal(sceneId) {
  const profile = state.profiles[sceneId];
  if (!profile) return;

  const modal = document.getElementById('modalLinkApp');
  const sceneNameEl = document.getElementById('linkAppSceneName');
  const selectEl = document.getElementById('selectRunningApps');
  const groupCustom = document.getElementById('groupCustomAppInput');
  const inputCustom = document.getElementById('inputCustomAppName');

  if (sceneNameEl) sceneNameEl.textContent = profile.name;
  if (groupCustom) groupCustom.style.display = 'none';
  if (inputCustom) inputCustom.value = profile.linked_app || '';

  if (selectEl) {
    selectEl.innerHTML = '<option value="">-- Carregando aplicativos do macOS... --</option>';
  }
  if (modal) modal.style.display = 'flex';

  try {
    const res = await fetch('/api/running_apps');
    const runningApps = await res.json();
    let opts = '<option value="">-- Nenhum (Troca Manual) --</option>';
    opts += '<optgroup label="Aplicativos Abertos no macOS">';
    
    let matched = false;
    runningApps.forEach(app => {
      const isSel = profile.linked_app && (profile.linked_app.toLowerCase() === app.name.toLowerCase());
      if (isSel) matched = true;
      opts += `<option value="${app.name}" ${isSel ? 'selected' : ''}>${app.name}</option>`;
    });
    opts += '</optgroup>';
    opts += '<option value="__custom__"' + (!matched && profile.linked_app ? ' selected' : '') + '>Outro aplicativo / Digitar nome...</option>';

    if (selectEl) {
      selectEl.innerHTML = opts;
      if (!matched && profile.linked_app) {
        if (groupCustom) groupCustom.style.display = 'block';
      }
      selectEl.onchange = () => {
        if (selectEl.value === '__custom__') {
          if (groupCustom) groupCustom.style.display = 'block';
        } else {
          if (groupCustom) groupCustom.style.display = 'none';
          if (inputCustom) inputCustom.value = selectEl.value;
        }
      };
    }
  } catch (err) {
    console.error('Erro ao listar running_apps:', err);
  }

  // Botão Salvar Vínculo
  const btnSave = document.getElementById('btnSaveLinkApp');
  if (btnSave) {
    btnSave.onclick = async () => {
      let chosen = selectEl.value;
      if (chosen === '__custom__') {
        chosen = inputCustom.value.trim();
      }
      showToast(`Vinculando "${profile.name}" ao app "${chosen || 'Nenhum'}"...`);
      try {
        const res = await fetch('/api/profile/link_app', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: sceneId, app: chosen })
        });
        if (res.ok) {
          profile.linked_app = chosen;
          renderSceneList();
          updateSceneInspector();
          if (modal) modal.style.display = 'none';
          showToast(`✓ Cena vinculada ao app "${chosen || 'Nenhum'}"`);
        }
      } catch (err) {
        showToast('Erro ao salvar vínculo de aplicativo');
      }
    };
  }

  // Botão Remover Vínculo
  const btnRemove = document.getElementById('btnRemoveLinkApp');
  if (btnRemove) {
    btnRemove.onclick = async () => {
      showToast(`Removendo vínculo de "${profile.name}"...`);
      try {
        const res = await fetch('/api/profile/link_app', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: sceneId, app: '' })
        });
        if (res.ok) {
          profile.linked_app = '';
          renderSceneList();
          updateSceneInspector();
          if (modal) modal.style.display = 'none';
          showToast('✓ Vínculo removido');
        }
      } catch (err) {
        showToast('Erro ao desvincular aplicativo');
      }
    };
  }
}

// Carregamento da Loja de Ícones Nativos
async function loadStoreIconPacks() {
  const tabsContainer = document.getElementById('storePackTabs');
  const iconsContainer = document.getElementById('storeIconsContainer');
  if (!tabsContainer || !iconsContainer) return;

  tabsContainer.innerHTML = '<span style="padding: 10px; font-size: 11px; color: #8e8e93;">Carregando pacotes de ícones nativos...</span>';
  iconsContainer.innerHTML = '';

  try {
    const res = await fetch('/api/icon_packs');
    const packs = await res.json();

    if (!packs || packs.length === 0) {
      tabsContainer.innerHTML = '';
      iconsContainer.innerHTML = '<div style="padding: 20px; color: #8e8e93; font-size: 12px;">Nenhum pacote de ícones encontrado no aplicativo oficial.</div>';
      return;
    }

    tabsContainer.innerHTML = '';
    packs.forEach((pack, idx) => {
      const tabBtn = document.createElement('button');
      tabBtn.className = `modal-tab-btn ${idx === 0 ? 'active' : ''}`;
      tabBtn.innerText = pack.name;
      tabBtn.onclick = () => {
        tabsContainer.querySelectorAll('.modal-tab-btn').forEach(b => b.classList.remove('active'));
        tabBtn.classList.add('active');
        renderPackIcons(pack);
      };
      tabsContainer.appendChild(tabBtn);
    });

    renderPackIcons(packs[0]);
  } catch (err) {
    iconsContainer.innerHTML = '<div style="padding: 20px; color: #ff3b30; font-size: 12px;">Erro ao carregar pacotes de ícones.</div>';
    console.error('Erro ao carregar icon_packs:', err);
  }
}

function renderPackIcons(pack) {
  const iconsContainer = document.getElementById('storeIconsContainer');
  if (!iconsContainer) return;
  iconsContainer.innerHTML = '';

  if (!pack.icons || pack.icons.length === 0) {
    iconsContainer.innerHTML = '<div style="padding: 20px; color: #8e8e93; font-size: 12px;">Nenhum ícone neste pacote.</div>';
    return;
  }

  pack.icons.forEach(icon => {
    const card = document.createElement('div');
    card.className = 'store-icon-card';
    card.title = `Clique para aplicar à tecla ${state.selectedSlot + 1}`;
    card.innerHTML = `
      <img class="store-icon-img" src="/api/image?path=${encodeURIComponent(icon.path)}" alt="">
      <span class="store-icon-name">${icon.name}</span>
    `;

    card.onclick = () => {
      const profile = state.profiles[state.activeProfile];
      if (!profile.keys) profile.keys = {};
      if (!profile.keys[state.selectedSlot]) {
        profile.keys[state.selectedSlot] = {
          title: icon.name,
          bg: '#18181b',
          textColor: '#ffffff',
          category: pack.name,
          actionType: 'none',
          actionName: icon.name
        };
      }
      const keyData = profile.keys[state.selectedSlot];
      keyData.imagePath = icon.path;
      renderDeckGrid();
      selectKey(state.selectedSlot);
      syncKeyToHardware(state.selectedSlot, keyData);
      closeModal('modalStore');
      showToast(`✓ Ícone "${icon.name}" aplicado à tecla ${state.selectedSlot + 1}!`);
    };

    iconsContainer.appendChild(card);
  });
}

// Carregamento da Biblioteca de Skins e Temas de 15 Telas
async function loadLayoutSkins() {
  const container = document.getElementById('skinGridContainer');
  if (!container) return;
  container.innerHTML = '<span style="padding: 10px; font-size: 11px; color: #8e8e93;">Carregando temas de 15 teclas oficiais...</span>';

  try {
    const res = await fetch('/api/skins');
    const skins = await res.json();

    if (!skins || skins.length === 0) {
      container.innerHTML = '<div style="padding: 20px; color: #8e8e93; font-size: 12px;">Nenhuma skin encontrada no aplicativo oficial.</div>';
      return;
    }

    container.innerHTML = '';
    skins.forEach(skin => {
      const card = document.createElement('div');
      card.className = 'skin-card';

      const previewImg = skin.images && skin.images.length > 0 ? `/api/image?path=${encodeURIComponent(skin.images[0])}` : '';

      card.innerHTML = `
        <img class="skin-preview-img" src="${previewImg}" alt="${skin.name}">
        <span class="skin-name">${skin.name}</span>
        <button class="skin-btn-apply">Aplicar este Tema</button>
      `;

      card.querySelector('.skin-btn-apply').onclick = async (e) => {
        e.stopPropagation();
        showToast(`Aplicando tema "${skin.name}" nas 15 teclas...`);
        try {
          const res = await fetch('/api/skin/apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ skin: skin.id, page: state.activeProfile })
          });
          const data = await res.json();
          if (data.success) {
            await loadServerState();
            closeModal('modalLayouts');
            showToast(`✓ Tema "${skin.name}" aplicado a todas as 15 teclas LCD!`);
          } else {
            showToast('Erro ao aplicar tema');
          }
        } catch (err) {
          showToast('Erro de comunicação ao aplicar tema');
        }
      };

      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = '<div style="padding: 20px; color: #ff3b30; font-size: 12px;">Erro ao carregar skins.</div>';
    console.error('Erro ao carregar skins:', err);
  }
}

function applyKeyColor(color, applyToAll = false) {
  const profile = state.profiles[state.activeProfile];
  if (!profile) return;

  if (applyToAll) {
    if (!profile.keys) profile.keys = {};
    for (let s = 0; s < 15; s++) {
      if (!profile.keys[s]) {
        profile.keys[s] = {
          title: '',
          subtitle: '',
          bg: color,
          textColor: '#ffffff',
          fontSize: 12,
          showTitle: true,
          actionType: 'none'
        };
      } else {
        profile.keys[s].bg = color;
        // Se tinha imagem de mural (fundo contínuo), remove para a cor sólida aparecer
        if (profile.keys[s].imagePath && profile.keys[s].imagePath.includes('mural_')) {
          delete profile.keys[s].imagePath;
        }
      }
      syncKeyToHardware(s, profile.keys[s]);
    }

    renderDeckGrid();
    if (state.selectedSlot !== null && state.selectedSlot !== undefined) {
      selectKey(state.selectedSlot);
    }
    showToast(`✓ Cor ${color} aplicada a todas as 15 telas LCD!`);
    return;
  }

  if (state.selectedSlot === null || state.selectedSlot === undefined) {
    showToast('Selecione uma tecla para alterar a cor.');
    return;
  }

  if (!profile.keys) profile.keys = {};
  let keyData = profile.keys[state.selectedSlot];
  if (!keyData) {
    keyData = {
      title: '',
      subtitle: '',
      bg: color,
      textColor: '#ffffff',
      fontSize: 12,
      showTitle: true,
      actionType: 'none'
    };
    profile.keys[state.selectedSlot] = keyData;
  } else {
    keyData.bg = color;
    // Se tinha imagem de mural recortada na tecla, remove para que a cor LCD real apareça!
    if (keyData.imagePath && keyData.imagePath.includes('mural_')) {
      delete keyData.imagePath;
    }
  }

  // Atualiza swatches ativas e display de cor no Inspector
  document.querySelectorAll('.swatch:not(.scene-swatch)').forEach(b => {
    b.classList.toggle('active', (b.dataset.color || '').toLowerCase() === color.toLowerCase());
  });
  const customPicker = document.getElementById('customColorPicker');
  if (customPicker) customPicker.value = color;
  const hexLabel = document.getElementById('currentColorHex');
  if (hexLabel) hexLabel.innerText = color;

  // Atualiza preview no card lateral
  const previewCard = document.getElementById('keyPreviewCard');
  if (previewCard) {
    previewCard.style.backgroundColor = color;
    const imgPreview = previewCard.querySelector('.preview-card-img');
    if (imgPreview && (!keyData.imagePath || keyData.imagePath.includes('mural_'))) {
      imgPreview.style.display = 'none';
    }
  }

  updateSlotVisual(state.selectedSlot, keyData);
  syncKeyToHardware(state.selectedSlot, keyData);
  showToast(`✓ Cor LCD definida: ${color}`);
}

function applySceneColor(color) {
  const profile = state.profiles[state.activeProfile];
  if (!profile) return;
  profile.sceneBg = color;

  if (!profile.keys) profile.keys = {};
  for (let s = 0; s < 15; s++) {
    if (!profile.keys[s]) {
      profile.keys[s] = {
        title: '',
        subtitle: '',
        bg: color,
        textColor: '#ffffff',
        fontSize: 12,
        showTitle: true,
        actionType: 'none'
      };
    } else {
      profile.keys[s].bg = color;
      if (profile.keys[s].imagePath && profile.keys[s].imagePath.includes('mural_')) {
        delete profile.keys[s].imagePath;
      }
    }
    syncKeyToHardware(s, profile.keys[s]);
  }

  document.querySelectorAll('.scene-swatch').forEach(b => {
    b.classList.toggle('active', (b.dataset.color || '').toLowerCase() === color.toLowerCase());
  });
  const scenePicker = document.getElementById('sceneCustomColorPicker');
  if (scenePicker) scenePicker.value = color;
  const sceneHex = document.getElementById('currentSceneColorHex');
  if (sceneHex) sceneHex.innerText = color;

  renderDeckGrid();
  if (state.selectedSlot !== null && state.selectedSlot !== undefined) {
    selectKey(state.selectedSlot);
  }
  showToast(`✓ Cor de fundo aplicada a todas as 15 telas LCD: ${color}`);
}

// Construtor completo e tolerante a falhas do payload de ação para o motor Fifine
function buildActionPayload(keyData) {
  if (!keyData) return null;
  const actType = keyData.actionType || getActionTypeFromUuid(keyData.uuid || keyData.actionUuid);

  if (actType === 'open' || keyData.path) {
    return {
      type: 'open',
      target: keyData.path,
      path: keyData.path,
      uuid: keyData.uuid || keyData.actionUuid || 'com.hotspot.streamdock.system.open'
    };
  }
  if (actType === 'text') {
    return {
      type: 'text',
      text: keyData.textPayload || keyData.text || '',
      enter: !!keyData.pressEnter,
      clipboard: keyData.useClipboard !== false,
      uuid: keyData.uuid || 'com.hotspot.streamdock.system.text'
    };
  }
  if (actType === 'hotkey' || keyData.hotkey) {
    return {
      type: 'hotkey',
      keys: keyData.hotkey || '',
      uuid: keyData.uuid || 'com.hotspot.streamdock.system.hotkey'
    };
  }
  if (actType === 'url' || keyData.url) {
    return {
      type: 'website',
      target: keyData.url || '',
      url: keyData.url || '',
      uuid: keyData.uuid || 'com.hotspot.streamdock.system.website'
    };
  }
  if (actType === 'soundboard' || keyData.uuid?.includes('soundboard') || keyData.uuid?.includes('audioplay')) {
    return {
      type: keyData.uuid || 'audioplay',
      path: keyData.path || keyData.target || '',
      target: keyData.path || keyData.target || '',
      uuid: keyData.uuid || 'com.hotspot.streamdock.soundboard.playaudio'
    };
  }
  if (actType === 'shell' || keyData.uuid?.includes('shell')) {
    return {
      type: 'shell',
      command: keyData.command || keyData.cmd || keyData.path || '',
      cmd: keyData.command || keyData.cmd || keyData.path || '',
      uuid: keyData.uuid || 'com.hotspot.streamdock.system.shell'
    };
  }
  if (actType === 'toggle' || keyData.uuid?.includes('toggle')) {
    return {
      type: 'toggle',
      uuid: keyData.uuid || 'com.hotspot.streamdock.system.toggle',
      title_a: keyData.title_a || '',
      title_b: keyData.title_b || '',
      keys_a: keyData.keys_a || '',
      keys_b: keyData.keys_b || '',
      bg_a: keyData.bg_a || '#14532d',
      bg_b: keyData.bg_b || '#7f1d1d',
      accent_a: keyData.accent_a || '#22c55e',
      accent_b: keyData.accent_b || '#ef4444',
      current_state: keyData.current_state || 0
    };
  }
  if (actType === 'folder' || keyData.uuid?.includes('openchild') || keyData.target?.startsWith('folder_')) {
    return {
      type: 'openchild',
      target: keyData.target || keyData.folderId,
      uuid: 'com.hotspot.streamdock.profile.openchild'
    };
  }
  if (actType === 'backtoparent' || keyData.uuid?.includes('backtoparent')) {
    return {
      type: 'backtoparent',
      target: keyData.target || 'principal',
      uuid: 'com.hotspot.streamdock.profile.backtoparent'
    };
  }
  if (actType === 'multiaction' || keyData.uuid?.includes('routine')) {
    return {
      type: 'multiaction',
      uuid: 'com.hotspot.streamdock.multiactions.routine',
      steps: keyData.steps || []
    };
  }
  if (actType === 'obs' || keyData.uuid?.includes('obsstudio') || keyData.actionUuid?.includes('obsstudio')) {
    return {
      type: keyData.uuid || keyData.actionUuid,
      uuid: keyData.uuid || keyData.actionUuid,
      sceneName: keyData.sceneName || '',
      sourceName: keyData.sourceName || '',
      sceneItemId: keyData.sceneItemId || null,
      visible: keyData.visible !== false
    };
  }
  return {
    type: keyData.uuid || keyData.actionType || 'none',
    uuid: keyData.uuid || '',
    ...keyData
  };
}

// Sincronização ultra-rápida não-bloqueante com o Hardware D6 Físico via API
function syncKeyToHardware(slot, keyData) {
  const payload = {
    key: slot + 1, // 1-indexado no hardware
    page: state.activeProfile,
    data: keyData ? {
      title: keyData.title || '',
      subtitle: keyData.subtitle || '',
      bg: keyData.bg || '#18181b',
      textColor: keyData.textColor || '#ffffff',
      fontSize: parseInt(keyData.fontSize) || 12,
      fontFamily: keyData.fontFamily || 'Helvetica',
      bold: !!keyData.bold,
      italic: !!keyData.italic,
      underline: !!keyData.underline,
      titleAlignment: keyData.titleAlignment || 'middle',
      showTitle: keyData.showTitle !== false,
      borderColor: keyData.borderColor || '',
      borderWidth: parseInt(keyData.borderWidth) || 0,
      imageFit: keyData.imageFit || 'cover',
      imagePath: keyData.imagePath || '',
      icon: keyData.icon || '',
      action: buildActionPayload(keyData)
    } : null
  };

  fetch('/api/key/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).catch(err => {
    console.warn('Sync com hardware não disponível:', err);
  });
}

// ================= INTEGRAÇÃO OBS STUDIO WEBSOCKET V5 =================
let currentObsStatus = null;

async function fetchObsStatus() {
  try {
    const res = await fetch('/api/obs/status');
    if (res.ok) {
      currentObsStatus = await res.json();
      
      // Atualiza Pílula do OBS no Top Header
      const hdrObsDot = document.getElementById('headerObsDot');
      const hdrObsText = document.getElementById('headerObsText');
      if (hdrObsDot && hdrObsText) {
        if (currentObsStatus && currentObsStatus.connected) {
          hdrObsDot.className = 'obs-status-dot connected';
          hdrObsText.innerText = 'Conectado';
        } else {
          hdrObsDot.className = 'obs-status-dot disconnected';
          hdrObsText.innerText = 'Desconectado';
        }
      }

      return currentObsStatus;
    }
  } catch (e) {
    console.warn('Erro ao consultar /api/obs/status:', e);
  }
  return null;
}

async function updateObsContextPanel(keyData) {
  const dot = document.getElementById('obsStatusDot');
  const text = document.getElementById('obsStatusText');
  const rowScene = document.getElementById('rowObsScene');
  const rowSceneCustom = document.getElementById('rowObsSceneCustom');
  const selectScene = document.getElementById('selectObsScene');
  const inputScene = document.getElementById('inputObsSceneName');
  const rowAudio = document.getElementById('rowObsAudio');
  const rowAudioCustom = document.getElementById('rowObsAudioCustom');
  const selectAudio = document.getElementById('selectObsAudio');
  const inputAudio = document.getElementById('inputObsAudioName');
  const rowSourceItem = document.getElementById('rowObsSourceItem');
  const inputItemId = document.getElementById('inputObsItemId');
  const btnTest = document.getElementById('btnTestObsAction');

  if (rowScene) rowScene.style.display = 'none';
  if (rowSceneCustom) rowSceneCustom.style.display = 'none';
  if (rowAudio) rowAudio.style.display = 'none';
  if (rowAudioCustom) rowAudioCustom.style.display = 'none';
  if (rowSourceItem) rowSourceItem.style.display = 'none';

  const obs = await fetchObsStatus();
  if (obs && obs.connected) {
    if (dot) dot.className = 'obs-status-dot connected';
    if (text) text.innerText = `OBS v5 Conectado (${obs.host}:${obs.port})`;
  } else {
    if (dot) dot.className = 'obs-status-dot disconnected';
    if (text) text.innerText = 'OBS Desconectado (Configurações > OBS Studio)';
  }

  const actType = (keyData.uuid || keyData.actionUuid || '').toLowerCase();

  // Ação de Cena
  if (actType.includes('scene')) {
    if (rowScene) rowScene.style.display = 'flex';
    if (rowSceneCustom) rowSceneCustom.style.display = 'flex';
    if (selectScene) {
      selectScene.innerHTML = '<option value="">-- Selecione a Cena --</option>';
      if (obs && obs.scenes && obs.scenes.length > 0) {
        obs.scenes.forEach(sc => {
          const opt = document.createElement('option');
          opt.value = sc;
          opt.innerText = sc + (sc === obs.current_scene ? ' (Ativa)' : '');
          if (sc === keyData.sceneName) opt.selected = true;
          selectScene.appendChild(opt);
        });
      }
      selectScene.onchange = () => {
        if (selectScene.value) {
          keyData.sceneName = selectScene.value;
          if (inputScene) inputScene.value = selectScene.value;
          keyData.title = selectScene.value.toUpperCase().slice(0, 10);
          const titleInput = document.getElementById('inputKeyTitle');
          if (titleInput) titleInput.value = keyData.title;
          const prevLabel = document.getElementById('previewKeyLabel');
          if (prevLabel) prevLabel.innerText = keyData.title;
          renderDeckGrid();
          syncKeyToHardware(state.selectedSlot, keyData);
        }
      };
    }
    if (inputScene) {
      inputScene.value = keyData.sceneName || '';
      inputScene.oninput = (e) => {
        keyData.sceneName = e.target.value;
        syncKeyToHardware(state.selectedSlot, keyData);
      };
    }
  }

  // Ação de Áudio / Mixer
  else if (actType.includes('mixeraudio') || actType.includes('audio')) {
    if (rowAudio) rowAudio.style.display = 'flex';
    if (rowAudioCustom) rowAudioCustom.style.display = 'flex';
    if (selectAudio) {
      selectAudio.innerHTML = '<option value="">-- Selecione a Fonte --</option>';
      if (obs && obs.audio_inputs && Object.keys(obs.audio_inputs).length > 0) {
        Object.keys(obs.audio_inputs).forEach(inp => {
          const opt = document.createElement('option');
          opt.value = inp;
          opt.innerText = inp;
          if (inp === keyData.sourceName) opt.selected = true;
          selectAudio.appendChild(opt);
        });
      }
      selectAudio.onchange = () => {
        if (selectAudio.value) {
          keyData.sourceName = selectAudio.value;
          if (inputAudio) inputAudio.value = selectAudio.value;
          keyData.title = selectAudio.value.toUpperCase().slice(0, 8);
          const titleInput = document.getElementById('inputKeyTitle');
          if (titleInput) titleInput.value = keyData.title;
          const prevLabel = document.getElementById('previewKeyLabel');
          if (prevLabel) prevLabel.innerText = keyData.title;
          renderDeckGrid();
          syncKeyToHardware(state.selectedSlot, keyData);
        }
      };
    }
    if (inputAudio) {
      inputAudio.value = keyData.sourceName || '';
      inputAudio.oninput = (e) => {
        keyData.sourceName = e.target.value;
        syncKeyToHardware(state.selectedSlot, keyData);
      };
    }
  }

  // Ação de Visibilidade de Fonte
  else if (actType.includes('source')) {
    if (rowSceneCustom) rowSceneCustom.style.display = 'flex';
    if (rowSourceItem) rowSourceItem.style.display = 'flex';
    if (inputScene) {
      inputScene.value = keyData.sceneName || '';
      inputScene.oninput = (e) => {
        keyData.sceneName = e.target.value;
        syncKeyToHardware(state.selectedSlot, keyData);
      };
    }
    if (inputItemId) {
      inputItemId.value = keyData.sceneItemId || '';
      inputItemId.oninput = (e) => {
        keyData.sceneItemId = parseInt(e.target.value) || 0;
        syncKeyToHardware(state.selectedSlot, keyData);
      };
    }
  }

  if (btnTest) {
    btnTest.onclick = async () => {
      btnTest.disabled = true;
      btnTest.innerText = 'Executando...';
      try {
        await fetch('/api/key/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: {
              type: keyData.uuid || keyData.actionUuid,
              uuid: keyData.uuid || keyData.actionUuid,
              sceneName: keyData.sceneName,
              sourceName: keyData.sourceName,
              sceneItemId: keyData.sceneItemId
            }
          })
        });
        showToast('✓ Ação enviada ao OBS Studio');
        setTimeout(() => updateObsContextPanel(keyData), 500);
      } catch (err) {
        showToast('Erro ao testar ação OBS: ' + err.message);
      } finally {
        btnTest.disabled = false;
        btnTest.innerText = 'Testar Ação no OBS Agora';
      }
    };
  }
}

function initObsSettings() {
  const btnSave = document.getElementById('btnSaveObsConfig');
  const btnConnect = document.getElementById('btnConnectObs');
  const inputHost = document.getElementById('settingObsHost');
  const inputPort = document.getElementById('settingObsPort');
  const inputPass = document.getElementById('settingObsPassword');
  const badge = document.getElementById('obsModalStatusBadge');
  const scenesList = document.getElementById('obsDetectedScenesList');

  async function refreshObsModal() {
    const obs = await fetchObsStatus();
    if (!obs) return;
    if (inputHost && obs.host) inputHost.value = obs.host;
    if (inputPort && obs.port) inputPort.value = obs.port;
    if (badge) {
      if (obs.connected && obs.identified) {
        badge.className = 'badge-status-connected';
        badge.innerText = 'Conectado (v5 RFC)';
      } else if (obs.connected) {
        badge.className = 'badge-status-disconnected';
        badge.innerText = 'Conectando / Handshake...';
      } else {
        badge.className = 'badge-status-disconnected';
        badge.innerText = 'Desconectado';
      }
    }
    if (scenesList) {
      if (obs.scenes && obs.scenes.length > 0) {
        scenesList.innerHTML = '';
        obs.scenes.forEach(sc => {
          const pill = document.createElement('span');
          pill.className = 'scene-pill' + (sc === obs.current_scene ? ' active' : '');
          pill.innerText = sc + (sc === obs.current_scene ? ' (Ao Vivo)' : '');
          scenesList.appendChild(pill);
        });
      } else {
        scenesList.innerHTML = '<span class="scene-pill-empty">Nenhuma cena detectada (OBS desconectado)</span>';
      }
    }
  }

  if (btnSave) {
    btnSave.onclick = async () => {
      btnSave.disabled = true;
      try {
        const host = inputHost ? inputHost.value.trim() : '127.0.0.1';
        const port = inputPort ? parseInt(inputPort.value) || 4455 : 4455;
        const password = inputPass ? inputPass.value : '';
        const res = await fetch('/api/obs/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host, port, password })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ Configurações do OBS salvas');
          setTimeout(refreshObsModal, 600);
        }
      } catch (e) {
        showToast('Erro ao salvar configuração OBS');
      } finally {
        btnSave.disabled = false;
      }
    };
  }

  if (btnConnect) {
    btnConnect.onclick = async () => {
      btnConnect.disabled = true;
      btnConnect.innerText = 'Conectando...';
      try {
        const res = await fetch('/api/obs/connect', { method: 'POST' });
        const data = await res.json();
        if (data.identified) {
          showToast('✓ Conectado com sucesso ao OBS Studio v5!');
        } else if (data.connected) {
          showToast('Conectado ao OBS, aguardando autenticação...');
        } else {
          showToast('Não foi possível conectar. Verifique se o OBS Studio está aberto na porta configurada.');
        }
        await refreshObsModal();
      } catch (e) {
        showToast('Erro na conexão com OBS Studio: ' + e.message);
      } finally {
        btnConnect.disabled = false;
        btnConnect.innerText = 'Conectar ao OBS';
      }
    };
  }

  // Monitora clique na aba tabOBS
  document.querySelectorAll('.modal-tab-btn[data-tab="tabOBS"]').forEach(btn => {
    btn.addEventListener('click', refreshObsModal);
  });
}



// ================= MODAL: MURAL 3x5 (PAPEL DE PAREDE CONTÍNUO) =================
function initWallpaperMuralModal() {
  const modal = document.getElementById('modalWallpaperMural');
  const btnOpen = document.getElementById('btnOpenWallpaperMural');
  const btnClose = document.getElementById('btnCloseWallpaperMural');
  const btnCancel = document.getElementById('btnCancelMural');
  const btnApply = document.getElementById('btnApplyMural');
  const dropZone = document.getElementById('muralDropZone');
  const fileInput = document.getElementById('fileInputMural');
  const previewContainer = document.getElementById('muralPreviewContainer');
  const previewImg = document.getElementById('muralPreviewImg');

  let currentMuralBase64 = null;

  if (!modal || !btnOpen) return;

  btnOpen.onclick = () => {
    modal.style.display = 'flex';
    currentMuralBase64 = null;
    if (previewContainer) previewContainer.style.display = 'none';
    if (btnApply) btnApply.disabled = true;
  };

  const closeModal = () => { modal.style.display = 'none'; };
  if (btnClose) btnClose.onclick = closeModal;
  if (btnCancel) btnCancel.onclick = closeModal;
  modal.onclick = (e) => { if (e.target === modal) closeModal(); };

  function handleImageFile(file) {
    if (!file || !file.type.startsWith('image/')) {
      showToast('Por favor selecione um arquivo de imagem válido (PNG, JPEG)');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      currentMuralBase64 = e.target.result;
      if (previewImg) previewImg.src = currentMuralBase64;
      if (previewContainer) previewContainer.style.display = 'block';
      if (btnApply) btnApply.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  if (dropZone && fileInput) {
    dropZone.onclick = () => fileInput.click();
    fileInput.onchange = (e) => {
      const file = e.target.files?.[0];
      if (file) handleImageFile(file);
      fileInput.value = '';
    };

    dropZone.ondragover = (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    };
    dropZone.ondragleave = () => dropZone.classList.remove('dragover');
    dropZone.ondrop = (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      const file = e.dataTransfer.files?.[0];
      if (file) handleImageFile(file);
    };
  }

  if (btnApply) {
    btnApply.onclick = async () => {
      if (!currentMuralBase64) return;
      btnApply.disabled = true;
      btnApply.innerText = 'Fatiando e enviando às 15 telas...';
      showToast('Processando mural panorâmico 3x5 via Pillow...');

      try {
        const res = await fetch('/api/wallpaper/mural', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            page: state.activeProfile,
            base64: currentMuralBase64
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast('✓ Mural 3x5 aplicado com sucesso nas 15 telas LCD!');
          await loadServerState();
          renderDeckGrid();
          selectKey(0);
          closeModal();
        } else {
          showToast('Erro ao aplicar mural: ' + (data.error || 'Falha no processamento'));
        }
      } catch (err) {
        showToast('Erro de conexão ao enviar papel de parede');
      } finally {
        btnApply.disabled = false;
        btnApply.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg><span>Fatiar e Aplicar no Deck Físico</span>';
      }
    };
  }
}

// ================= GERENCIADOR DE TEMAS (DARK / LIGHT / AUTO) =================
function initThemeManager() {
  const savedTheme = localStorage.getItem('fifine_studio_theme') || 'dark';

  function getEffectiveTheme(preference) {
    if (preference === 'auto') {
      return (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
    }
    return preference;
  }

  function applyTheme(preference, notify = false) {
    localStorage.setItem('fifine_studio_theme', preference);
    const effective = getEffectiveTheme(preference);

    document.documentElement.setAttribute('data-theme', effective);
    document.body.classList.toggle('theme-light', effective === 'light');

    // Atualiza botões pill na aba de Ajustes > Geral
    const pills = document.querySelectorAll('.theme-switcher-pills .theme-pill-btn');
    pills.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.themeVal === preference);
    });

    // Atualiza botão de atalho rápido no header
    const quickBtn = document.getElementById('btnQuickThemeToggle');
    if (quickBtn) {
      const darkIcon = quickBtn.querySelector('.icon-theme-dark');
      const lightIcon = quickBtn.querySelector('.icon-theme-light');
      const label = quickBtn.querySelector('#lblThemeMode');
      if (effective === 'light') {
        if (darkIcon) darkIcon.style.display = 'none';
        if (lightIcon) lightIcon.style.display = 'block';
        if (label) label.innerText = 'Claro';
        quickBtn.title = 'Modo Claro ativo (clique para alternar para Escuro)';
      } else {
        if (darkIcon) darkIcon.style.display = 'block';
        if (lightIcon) lightIcon.style.display = 'none';
        if (label) label.innerText = 'Escuro';
        quickBtn.title = 'Modo Escuro ativo (clique para alternar para Claro)';
      }
    }

    if (notify) {
      const name = preference === 'auto' ? `Automático (${effective === 'light' ? 'Claro' : 'Escuro'})` : (preference === 'light' ? 'Modo Claro' : 'Modo Escuro');
      showToast(`✓ Tema: ${name}`);
    }
  }

  // Binds nas pills de ajuste
  const pills = document.querySelectorAll('.theme-switcher-pills .theme-pill-btn');
  pills.forEach(btn => {
    btn.onclick = () => {
      const choice = btn.dataset.themeVal || 'dark';
      applyTheme(choice, true);
    };
  });

  // Bind no botão de atalho rápido no header
  const quickBtn = document.getElementById('btnQuickThemeToggle');
  if (quickBtn) {
    quickBtn.onclick = () => {
      const current = localStorage.getItem('fifine_studio_theme') || 'dark';
      const effective = getEffectiveTheme(current);
      const next = effective === 'light' ? 'dark' : 'light';
      applyTheme(next, true);
    };
  }

  // Listener para preferência do sistema se estiver em 'auto'
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
      const current = localStorage.getItem('fifine_studio_theme') || 'dark';
      if (current === 'auto') {
        applyTheme('auto', false);
      }
    });
  }

  // Aplicação inicial imediata
  applyTheme(savedTheme, false);
}




