/* Progressive navigation + persisted light/dark preference. No dependencies. */
(() => {
  'use strict';
  const root = document.documentElement;
  const toggle = document.querySelector('.menu-toggle');
  const menu = document.getElementById('primary-nav');
  function closeMenu(returnFocus = false) {
    if (!toggle || !menu) return;
    toggle.setAttribute('aria-expanded', 'false');
    menu.dataset.open = 'false';
    if (returnFocus) toggle.focus();
  }
  if (toggle && menu) {
    toggle.addEventListener('click', () => {
      const open = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', String(open));
      menu.dataset.open = String(open);
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') closeMenu(true);
    });
    menu.addEventListener('click', e => { if (e.target.closest('a')) closeMenu(); });
    document.addEventListener('click', e => { if (!e.target.closest('.site-header')) closeMenu(); });
    matchMedia('(min-width:851px)').addEventListener('change', () => closeMenu());
  }
  const theme = document.querySelector('.theme-toggle');
  const prefersDark = matchMedia('(prefers-color-scheme:dark)');
  const isDark = () => root.dataset.theme === 'dark' || (!root.dataset.theme && prefersDark.matches);
  function updateThemeLabel() {
    if (theme) theme.setAttribute('aria-label', `Switch to ${isDark() ? 'light' : 'dark'} theme`);
  }
  if (theme) {
    theme.addEventListener('click', () => {
      root.dataset.theme = isDark() ? 'light' : 'dark';
      try { localStorage.setItem('big7-theme', root.dataset.theme); } catch (_) { /* memory-only preference */ }
      updateThemeLabel();
    });
    prefersDark.addEventListener('change', updateThemeLabel);
    updateThemeLabel();
  }
  const y = document.getElementById('year');
  if (y) y.textContent = new Date().getFullYear();
})();
