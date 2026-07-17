/* ═══════════════════════════════════════════════════════════════════
   big7.js — shared money-path JS for big7construction.com
   Loaded via <script defer src="/big7.js"> on every page (home + lanes).
   One copy so the intake form, prefill, and analytics cannot drift
   between pages (LAW #6/7 — money code). Tests parse THIS file:
   test_conversion.py · test_url_prefill.py · test_intake_analytics.py.
   Decorative page-specific JS (progress rail, parallax, ticker, menu)
   stays inline on its own page — do not move it here.
   ═══════════════════════════════════════════════════════════════════ */

/* Page slug for analytics payloads: '/' → 'home',
   '/commercial-industrial.html' → 'commercial-industrial', etc. */
var BIG7_PAGE = (function () {
  var p = window.location.pathname.replace(/\/+$/, '') || '/';
  if (p === '/' || p === '/index.html') return 'home';
  return p.replace(/^\//, '').replace(/\.html$/, '');
})();

// ─── Form submit: POST to Formspree via fetch, keep the user
//     on-page. Falls back to the native form action if fetch fails.
async function submitForm(e) {
  e.preventDefault();
  const form = e.target;
  const btn = document.getElementById('formBtn');
  const note = document.querySelector('.form-note');
  const original = btn.textContent;
  btn.textContent = 'Sending…';
  btn.disabled = true;

  try {
    const res = await fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) throw new Error('Formspree returned ' + res.status);
    btn.textContent = 'Request received ✓';
    btn.style.background = '#2F5D3A';
    form.querySelectorAll('input, select, textarea').forEach(f => f.disabled = true);
    if (note) note.textContent = "A senior estimator will reach out within 48 hours. Drawings + specs can be emailed to info@big7construction.com.";
  } catch (err) {
    btn.textContent = original;
    btn.disabled = false;
    if (note) note.textContent = "Something went wrong sending the form. Email info@big7construction.com directly or call (555) 700-0007.";
  }
}

// ─── Conversion: data-intent → prefill + attribution ─
// CONVERSION_STANDARDS.md § 2 (intent), § 3 (prefill), § 4 (events).
// Every service/portfolio CTA carries data-intent; on click we prefill
// the contact form's projectType radio + textarea hint (so the visitor
// never faces a blank form) and push a cta_click event to window.dataLayer
// (GA4-compatible) so future analytics can measure funnel without code changes.
// On pages whose form carries only a subset of the projectType radios,
// prefill degrades gracefully: a missing radio value simply no-ops.
(function () {
  const INTENT_TO_TYPE = {
    'service:enterprise-framing':   'commercial-new',
    'service:commercial-new':       'commercial-new',
    'service:industrial-warehouse': 'industrial-warehouse',
    'service:tenant-improvement':   'tenant-improvement',
    'service:custom-home':          'residential-custom',
    'service:structural-repair':    'residential-remodel',
    'service:trades-only':          'trades-only',
    'portfolio:industrial-01':      'industrial-warehouse',
    'portfolio:tenant-02':          'tenant-improvement',
    'portfolio:custom-home-03':     'residential-custom',
    'portfolio:commercial-04':      'commercial-new',
    'portfolio:residential-05':     'residential-remodel',
    'portfolio:structural-06':      'residential-remodel'
  };
  const PREFILL_MARK = '— Interested in: ';
  function track(name, props) {
    const payload = Object.assign({ event: name }, props || {});
    (window.dataLayer = window.dataLayer || []).push(payload);
  }
  function labelFor(el) {
    const title = el.querySelector('.service-title, .pf-title, .type-name');
    const raw = (title && title.textContent) || el.getAttribute('aria-label') || '';
    return raw.replace(/\s+/g, ' ').trim().slice(0, 80);
  }
  function prefill(intent, label) {
    const pt = INTENT_TO_TYPE[intent];
    if (pt) {
      const radio = document.querySelector('input[name="projectType"][value="' + pt + '"]');
      const already = document.querySelector('input[name="projectType"]:checked');
      if (radio && !already) radio.checked = true;
    }
    const ta = document.querySelector('form.cform textarea[name="message"]');
    if (ta && label) {
      const trimmed = ta.value.trim();
      if (!trimmed || trimmed.indexOf(PREFILL_MARK) === 0) {
        ta.value = PREFILL_MARK + label + '\n\n';
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }
  }
  document.addEventListener('click', function (e) {
    const el = e.target.closest('[data-intent]');
    if (!el) return;
    const intent = el.getAttribute('data-intent');
    const label = labelFor(el);
    // Position = intent segment after the namespace (`bid:hero` → `hero`,
    // `service:enterprise-framing` → `enterprise-framing`). Satisfies
    // CONVERSION_STANDARDS.md § 4 `cta_click.position` requirement so
    // funnel views can split by page region without a code change.
    const position = (intent.split(':')[1] || 'unspecified');
    track('cta_click', { intent: intent, page: BIG7_PAGE, position: position, label: label });
    prefill(intent, label);
  });
  const form = document.querySelector('form.cform');
  if (form) {
    // intake_start — CONVERSION_STANDARDS.md § 4. Fires once, on the
    // visitor's first focus into any intake-form field. Without it, the
    // funnel has a hidden hole between cta_click and intake_submit: we
    // cannot tell "clicked CTA but bailed on the form" from "never
    // touched the form at all." The `intakeStarted` guard is a
    // closure-scoped boolean (not a data-attribute) so a DOM re-render
    // cannot silently un-guard it and re-fire.
    let intakeStarted = false;
    form.addEventListener('focusin', function () {
      if (intakeStarted) return;
      intakeStarted = true;
      const checked = document.querySelector('input[name="projectType"]:checked');
      track('intake_start', {
        intent: checked ? 'type:' + checked.value : 'type:unset',
        page: BIG7_PAGE
      });
    }, true);
    form.addEventListener('submit', function () {
      const checked = document.querySelector('input[name="projectType"]:checked');
      const ta = form.querySelector('textarea[name="message"]');
      // `src` mirrors the hidden `source` input the landing IIFE writes
      // from ?src= / ?utm_source=. Without it in the payload, Formspree
      // gets the attribution but GA4/Plausible see intake_submit blind —
      // "which lane page produced the intake?" is unanswerable at the
      // funnel-view surface even though the data reached the estimator's
      // inbox. Same drift class the tick-27 lane-attribution loop closed
      // at the Formspree surface; this closes it at the dataLayer surface.
      const srcField = form.querySelector('input[name="source"]');
      track('intake_submit', {
        intent: checked ? 'type:' + checked.value : 'type:unset',
        has_prefill: !!(ta && ta.value.indexOf(PREFILL_MARK) === 0),
        message_length: ta ? ta.value.trim().length : 0,
        page: BIG7_PAGE,
        src: (srcField && srcField.value) || ''
      });
    }, true);
  }

  // ─── URL-param prefill (bio-link landing) ────────────────
  // Money path: a TikTok / Instagram / email-footer bio link like
  //   https://big7construction.com/commercial-industrial.html?intent=service:tenant-improvement&src=tiktok-bio
  // lands the visitor on a form that already knows why they came.
  // Also accepts `?type=<projectType>` (direct radio value — bio-link
  // authors can pick from the radio values without knowing the
  // internal intent slug) and `?src=<slug>` OR `?utm_source=<slug>`
  // for attribution. Every param is whitelisted through SAFE_PARAM
  // before touching the DOM — a URL param NEVER hits querySelector raw.
  // Reuses INTENT_TO_TYPE / PREFILL_MARK / labelFor / track from the
  // closure above so the mapping stays single-source-of-truth (a slug
  // rename locked by test_conversion.py auto-propagates to landing).
  (function () {
    try {
      const params = new URLSearchParams(window.location.search);
      const SAFE_PARAM = /^[a-z0-9:_\-]{1,64}$/i;
      const safe = (v) => (v && SAFE_PARAM.test(v)) ? v : '';
      const intent = safe(params.get('intent'));
      const type = safe(params.get('type'));
      const src = safe(params.get('src')) || safe(params.get('utm_source'));
      if (!intent && !type && !src) return;
      const resolvedType = type || (intent && INTENT_TO_TYPE[intent]) || '';
      let didRadio = false;
      if (resolvedType) {
        const radio = document.querySelector('input[name="projectType"][value="' + resolvedType + '"]');
        const already = document.querySelector('input[name="projectType"]:checked');
        if (radio && !already) { radio.checked = true; didRadio = true; }
      }
      let didText = false;
      if (intent) {
        const cta = document.querySelector('[data-intent="' + intent + '"]');
        let label = cta ? labelFor(cta) : '';
        if (!label) {
          const slug = intent.split(':')[1] || intent;
          label = slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        }
        const ta = document.querySelector('form.cform textarea[name="message"]');
        if (ta && (!ta.value || !ta.value.trim())) {
          ta.value = PREFILL_MARK + label + '\n\n';
          didText = true;
        }
      }
      // Persist `src` into the hidden `source` input so Formspree receives
      // lane attribution on submit. Lane forms ship a non-empty per-page
      // default (e.g. `commercial-industrial-page`), so an explicit
      // ?src=/?utm_source= param OVERWRITES the default — the bio link
      // that drove the click is more specific attribution than the page
      // it landed on. Without the overwrite the estimator sees an intake
      // with no idea which bio link drove the click.
      let didSource = false;
      if (src) {
        const srcField = document.querySelector('form.cform input[name="source"]');
        if (srcField && srcField.value !== src) { srcField.value = src; didSource = true; }
      }
      track('landing_prefill', {
        intent: intent, type: resolvedType, src: src, page: BIG7_PAGE,
        did_radio: didRadio, did_text: didText, did_source: didSource
      });
    } catch (_) { /* never break the page on a malformed URL */ }
  })();
})();

// ─── Analytics adapter: dataLayer → gtag/plausible bridge ─
// The IIFE above already pushes `cta_click` + `intake_submit` to
// `window.dataLayer` (GA4-compatible payload shape). This adapter
// monkey-patches `dataLayer.push` so every future push is mirrored
// to whichever consumer script is loaded — none, GA4, Plausible, or
// both. Michael's zero-code activation (add to each page's <head>):
//   GA4:      <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXX"></script>
//             <script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-XXXXXXX');</script>
//   Plausible: <script defer data-domain="big7construction.com" src="https://plausible.io/js/script.js"></script>
// Dropping either tag turns the funnel on with zero code changes. The
// adapter no-ops on gtag's own `arguments`-shaped pushes (no `.event`
// property → skipped) so there's no forwarding loop when both are live.
(function () {
  var dl = window.dataLayer = window.dataLayer || [];
  var origPush = Array.prototype.push.bind(dl);
  dl.push = function (evt) {
    var r = origPush(evt);
    try {
      if (evt && evt.event) {
        var props = {};
        for (var k in evt) {
          if (k !== 'event' && Object.prototype.hasOwnProperty.call(evt, k)) props[k] = evt[k];
        }
        if (typeof window.gtag === 'function') window.gtag('event', evt.event, props);
        if (typeof window.plausible === 'function') window.plausible(evt.event, { props: props });
      }
    } catch (_) { /* never break the click */ }
    return r;
  };
})();

// ─── Year in footer ───────────────────────────────────
(function () { const y = document.getElementById('year'); if (y) y.textContent = new Date().getFullYear(); })();
