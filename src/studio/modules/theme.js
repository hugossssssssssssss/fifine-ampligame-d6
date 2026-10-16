/**
 * fifine Control Deck Studio Pro - Theme Module
 * Gerencia a alternância e persistência do Modo Claro (Light Mode) e Modo Escuro (Dark Mode).
 */

const THEME_STORAGE_KEY = 'fifine_studio_theme';

export function initTheme() {
  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) || 'dark';
  applyTheme(savedTheme);

  const btnToggle = document.getElementById('btnQuickThemeToggle');
  const selSetting = document.getElementById('settingThemeModeSelect');

  if (btnToggle) {
    btnToggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
    });
  }

  if (selSetting) {
    selSetting.value = savedTheme;
    selSetting.addEventListener('change', (e) => {
      applyTheme(e.target.value);
    });
  }
}

export function applyTheme(themeName) {
  const isLight = themeName === 'light';
  document.documentElement.setAttribute('data-theme', themeName);
  localStorage.setItem(THEME_STORAGE_KEY, themeName);

  const darkIcon = document.querySelector('.icon-theme-dark');
  const lightIcon = document.querySelector('.icon-theme-light');
  const lblTheme = document.getElementById('lblThemeMode');
  const selSetting = document.getElementById('settingThemeModeSelect');

  if (darkIcon && lightIcon) {
    darkIcon.style.display = isLight ? 'none' : 'block';
    lightIcon.style.display = isLight ? 'block' : 'none';
  }

  if (lblTheme) {
    lblTheme.textContent = isLight ? 'Claro' : 'Escuro';
  }

  if (selSetting && selSetting.value !== themeName) {
    selSetting.value = themeName;
  }
}
