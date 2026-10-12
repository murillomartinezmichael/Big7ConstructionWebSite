/* Big 7 candidate: adapted from the inspected shared intake code at
   c5a26edf4de61eae360e625af25ab6085edacb90. Same Formspree endpoint,
   delivery guard, receipt shape, attribution keys and optional mirror.
   Preview pages cannot send, including with JavaScript disabled. */
'use strict';
var BIG7_PAGE = (function () {
  var p = window.location.pathname.replace(/\/+$/, '') || '/';
  return p === '/' || p === '/index.html' ? 'home' : p.replace(/^\//, '').replace(/\.html$/, '');
})();
var BIG7_SUBMISSIONS = new WeakMap();
function big7Track(event, props) {
  const payload = Object.assign({ event: event }, props || {});
  (window.dataLayer = window.dataLayer || []).push(payload);
}
async function submitForm(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('#formBtn');
  const note = form.querySelector('.form-note');
  if (!btn || !note) return;
  note.setAttribute('role', 'status');
  note.setAttribute('aria-atomic', 'true');
  if (document.documentElement.hasAttribute('data-preview')) {
    note.textContent = 'Preview only — nothing has been sent. Your details remain in this form.';
    note.dataset.state = 'preview';
    return;
  }
  if (!form.reportValidity() || BIG7_SUBMISSIONS.has(form)) return;
  const trap = form.querySelector('input[name="website"]');
  if (trap && trap.value) {
    note.textContent = 'We could not send this request. Please contact Big 7 by email.';
    note.dataset.state = 'error';
    return;
  }
  BIG7_SUBMISSIONS.set(form, 'pending');
  const original = btn.innerHTML;
  note.textContent = 'Sending your request…';
  note.dataset.state = 'pending';
  btn.textContent = 'Sending…';
  btn.disabled = true;
  try {
    const mirror = new URLSearchParams();
    new FormData(form).forEach((v, k) => {
      if (k !== 'website' && k !== '_subject' && k !== '_replyto') mirror.append(k, v);
    });
    fetch('https://michaelmurillo.app.n8n.cloud/webhook/big7-lead-6463ba1dfc556282d338d554', {
      method: 'POST', body: mirror, keepalive: true
    }).catch(() => {});
  } catch (_) { /* Optional mirror never decides receipt or success. */ }
  let timeout;
  try {
    const controller = new AbortController();
    timeout = setTimeout(() => controller.abort(), 30000);
    const res = await fetch(form.action, {
      method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' },
      signal: controller.signal, redirect: 'error'
    });
    if (!res.ok || res.redirected ||
        (res.headers.get('content-type') || '').split(';')[0].trim().toLowerCase() !== 'application/json') {
      throw new Error('Unconfirmed Formspree response');
    }
    const receipt = await res.json();
    if (!receipt || Array.isArray(receipt) || typeof receipt !== 'object' ||
        typeof receipt.next !== 'string' || 'error' in receipt || 'errors' in receipt) {
      throw new Error('Unconfirmed Formspree receipt');
    }
    BIG7_SUBMISSIONS.set(form, 'accepted');
    btn.textContent = 'Request received ✓';
    note.textContent = 'Thank you. Your request has been received. Big 7 can contact you using the details you provided.';
    note.dataset.state = 'success';
    form.querySelectorAll('input, select, textarea').forEach(f => { f.disabled = true; });
    big7Track('intake_confirmed', { page: BIG7_PAGE, transport: 'formspree' });
  } catch (_) {
    if (BIG7_SUBMISSIONS.get(form) === 'accepted') return;
    BIG7_SUBMISSIONS.delete(form);
    btn.innerHTML = original;
    btn.disabled = false;
    note.dataset.state = 'error';
    note.textContent = 'We could not confirm receipt. Your details are still here; a request may already have arrived. To avoid a duplicate, email info@big7construction.com before retrying.';
    big7Track('intake_unconfirmed', { page: BIG7_PAGE });
  } finally { clearTimeout(timeout); }
}
(function () {
  const INTENT_TO_TYPE = {
    'service:enterprise-framing': 'commercial-new', 'service:commercial-new': 'commercial-new',
    'service:industrial-warehouse': 'industrial-warehouse', 'service:tenant-improvement': 'tenant-improvement',
    'service:custom-home': 'residential-custom', 'service:structural-repair': 'residential-remodel',
    'service:trades-only': 'trades-only', 'service:drywall': 'trades-only',
    'portfolio:industrial-01': 'industrial-warehouse', 'portfolio:tenant-02': 'tenant-improvement',
    'portfolio:custom-home-03': 'residential-custom', 'portfolio:commercial-04': 'commercial-new',
    'portfolio:residential-05': 'residential-remodel', 'portfolio:structural-06': 'residential-remodel'
  };
  const PREFILL_MARK = '— Interested in: ';
  const SAFE_PARAM = /^[a-z0-9:_\-]{1,64}$/i;
  const safe = v => v && SAFE_PARAM.test(v) ? v : '';
  const form = document.querySelector('form.cform');
  function labelFor(el) {
    const title = el.querySelector('.service-title, .pf-title, .type-name');
    return ((title && title.textContent) || el.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().slice(0,80);
  }
  function selectType(type) {
    if (!form || !safe(type)) return false;
    const radio = form.querySelector('input[name="projectType"][value="' + type + '"]');
    if (radio && !form.querySelector('input[name="projectType"]:checked')) { radio.checked = true; return true; }
    return false;
  }
  function prefill(intent, label) {
    selectType(INTENT_TO_TYPE[intent]);
    const ta = form && form.querySelector('textarea[name="message"]');
    if (ta && label && (!ta.value.trim() || ta.value.trim().indexOf(PREFILL_MARK) === 0)) {
      ta.value = PREFILL_MARK + label + '\n\n';
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }
  document.addEventListener('click', e => {
    const el = e.target.closest('[data-intent]');
    if (!el) return;
    const intent = el.getAttribute('data-intent');
    const label = labelFor(el);
    big7Track('cta_click', { intent: intent, page: BIG7_PAGE, position: intent.split(':')[1] || 'unspecified', label: label });
    prefill(intent, label);
  });
  if (form) {
    let intakeStarted = false;
    form.addEventListener('focusin', () => {
      if (intakeStarted) return;
      intakeStarted = true;
      const checked = form.querySelector('input[name="projectType"]:checked');
      big7Track('intake_start', { intent: checked ? 'type:' + checked.value : 'type:unset', page: BIG7_PAGE });
    }, true);
    form.addEventListener('submit', () => {
      if (document.documentElement.hasAttribute('data-preview')) return;
      const checked = form.querySelector('input[name="projectType"]:checked');
      const ta = form.querySelector('textarea[name="message"]');
      const src = form.querySelector('input[name="source"]');
      big7Track('intake_submit', {
        intent: checked ? 'type:' + checked.value : 'type:unset',
        has_prefill: !!(ta && ta.value.indexOf(PREFILL_MARK) === 0),
        message_length: ta ? ta.value.trim().length : 0, page: BIG7_PAGE, src: src ? src.value : ''
      });
    }, true);
    const email = form.querySelector('[name="email"]');
    if (email) email.addEventListener('input', () => {
      const reply = form.querySelector('[name="_replyto"]'); if (reply) reply.value = email.value;
    });
  }
  try {
    const params = new URLSearchParams(window.location.search);
    const intent = safe(params.get('intent')), type = safe(params.get('type'));
    const src = safe(params.get('src')) || safe(params.get('utm_source'));
    if (!intent && !type && !src) return;
    const resolved = type || INTENT_TO_TYPE[intent] || '';
    const didRadio = selectType(resolved);
    let didText = false, didSource = false;
    if (intent && form) {
      const cta = document.querySelector('[data-intent="' + intent + '"]');
      const label = cta ? labelFor(cta) : (intent.split(':')[1] || intent).replace(/-/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
      const ta = form.querySelector('textarea[name="message"]');
      if (ta && !ta.value.trim()) { ta.value = PREFILL_MARK + label + '\n\n'; didText = true; }
    }
    const srcField = form && form.querySelector('input[name="source"]');
    if (src && srcField && srcField.value !== src) { srcField.value = src; didSource = true; }
    big7Track('landing_prefill', { intent: intent, type: resolved, src: src, page: BIG7_PAGE,
      did_radio: didRadio, did_text: didText, did_source: didSource });
  } catch (_) { /* Malformed queries never break the page. */ }
})();
/* Existing analytics consumers remain optional; no new tracking provider. */
(function () {
  var dl = window.dataLayer = window.dataLayer || [];
  var origPush = Array.prototype.push.bind(dl);
  dl.push = function (evt) {
    var r = origPush(evt);
    try {
      if (evt && evt.event) {
        var props = {};
        for (var k in evt) if (k !== 'event' && Object.prototype.hasOwnProperty.call(evt,k)) props[k] = evt[k];
        if (typeof window.gtag === 'function') window.gtag('event',evt.event,props);
        if (typeof window.plausible === 'function') window.plausible(evt.event,{ props:props });
      }
    } catch (_) { /* Observation must not block the form. */ }
    return r;
  };
})();
