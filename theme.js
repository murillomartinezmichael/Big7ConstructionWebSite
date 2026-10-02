/* Light/dark toggle. The saved choice is applied before paint by the inline
   snippet in each page's <head>; this adds the button and flips the theme.
   Decorative/preference code only — the money path stays in big7.js. */
(function () {
  var root = document.documentElement;
  var osLight = window.matchMedia('(prefers-color-scheme: light)');
  function current() { return root.dataset.theme || (osLight.matches ? 'light' : 'dark'); }

  var button = document.createElement('button');
  button.type = 'button';
  button.className = 'theme-toggle';
  button.setAttribute('data-cta', 'theme-toggle');
  button.innerHTML =
    '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="4.25" stroke="currentColor" stroke-width="1.75"/><path d="M12 2.5v2.25M12 19.25v2.25M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.25M19.25 12h2.25M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/></svg>' +
    '<svg class="icon-moon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20 14.5A8.25 8.25 0 0 1 9.5 4a8.25 8.25 0 1 0 10.5 10.5Z" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/></svg>';

  function sync() {
    var next = current() === 'light' ? 'dark' : 'light';
    button.setAttribute('aria-label', 'Switch to ' + next + ' mode');
    button.title = 'Switch to ' + next + ' mode';
  }
  button.addEventListener('click', function () {
    var next = current() === 'light' ? 'dark' : 'light';
    root.dataset.theme = next;
    try { localStorage.setItem('big7-theme', next); } catch (e) {}
    sync();
  });
  if (osLight.addEventListener) osLight.addEventListener('change', sync);
  sync();
  document.body.appendChild(button);
})();
