/**
 * fifine Control Deck Studio Pro - API Service Module
 * Camada unificada para todas as chamadas REST com tratamento de erros e notificações toast.
 */

export function showToast(msg, duration = 2000) {
  const t = document.getElementById('syncToast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('visible');
  clearTimeout(t._hideTimer);
  t._hideTimer = setTimeout(() => {
    t.classList.remove('visible');
  }, duration);
}

export async function apiGetState() {
  const res = await fetch('/api/state?_t=' + Date.now());
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return await res.json();
}

export async function apiUpdateKey(pageId, slotNumber, keyData) {
  const res = await fetch('/api/key/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      page: pageId,
      key: slotNumber,
      data: keyData
    })
  });
  return await res.json();
}

export async function apiSelectPage(pageId) {
  const res = await fetch('/api/page/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ page: pageId })
  });
  return await res.json();
}

export async function apiCreatePage(pageId, name) {
  const res = await fetch('/api/page/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: pageId, name: name })
  });
  return await res.json();
}

export async function apiDeletePage(pageId) {
  const res = await fetch('/api/page/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: pageId })
  });
  return await res.json();
}

export async function apiRenameProfile(profileId, newName) {
  const res = await fetch('/api/profile/rename', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: profileId, name: newName })
  });
  return await res.json();
}

export async function apiDuplicateProfile(profileId) {
  const res = await fetch('/api/profile/duplicate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: profileId })
  });
  return await res.json();
}

export async function apiLinkApp(profileId, appName) {
  const res = await fetch('/api/profile/link_app', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: profileId, app: appName })
  });
  return await res.json();
}

export async function apiToggleAutoSwitch(enabled) {
  const res = await fetch('/api/autoswitch/toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled: enabled })
  });
  return await res.json();
}

export async function apiSetBrightness(percent) {
  const res = await fetch('/api/brightness', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ percent: percent })
  });
  return await res.json();
}

export async function apiSetLedSleepFollow(enabled) {
  const res = await fetch('/api/settings/led_sleep_follow', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled: enabled })
  });
  return await res.json();
}

export async function apiSetScreenOff(seconds) {
  const res = await fetch('/api/screen_off', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seconds: seconds })
  });
  return await res.json();
}

export async function apiDeviceSleep() {
  const res = await fetch('/api/device/sleep', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

export async function apiDeviceWake() {
  const res = await fetch('/api/device/wake', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

export async function apiExecuteKey(slot, action) {
  const res = await fetch('/api/key/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slot: slot, action: action })
  });
  return await res.json();
}

export async function apiSyncDeck() {
  const res = await fetch('/api/deck/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

export async function apiConnectHardware() {
  const res = await fetch('/api/connect');
  return await res.json();
}

export async function apiBrowseApps() {
  const res = await fetch('/api/browse_app');
  return await res.json();
}

export async function apiRunningApps() {
  const res = await fetch('/api/running_apps');
  return await res.json();
}

export async function apiGetObsStatus() {
  const res = await fetch('/api/obs/status');
  return await res.json();
}

export async function apiSaveObsConfig(host, port, password) {
  const res = await fetch('/api/obs/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host, port, password })
  });
  return await res.json();
}

export async function apiConnectObs() {
  const res = await fetch('/api/obs/connect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  return await res.json();
}

export async function apiObsAction(action, data = {}) {
  const res = await fetch('/api/obs/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, data })
  });
  return await res.json();
}

export async function apiGetIconLibrary() {
  const res = await fetch('/api/icons/library');
  return await res.json();
}

export async function apiUploadImage(filename, base64Data) {
  const res = await fetch('/api/upload_image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, base64: base64Data })
  });
  return await res.json();
}

export async function apiApplyMural(pageId, imagePath, base64Data) {
  const res = await fetch('/api/wallpaper/mural', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ page: pageId, path: imagePath, base64: base64Data })
  });
  return await res.json();
}
