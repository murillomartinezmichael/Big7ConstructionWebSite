'use strict';
var BIG7_PAGE = (function () {
  var p = window.location.pathname.slice(24).replace(/\/+$/, '') || '/';
  return p === '/' || p === '/index.html' ? 'home' : p.replace(/^\//, '').replace(/\.html$/, '');
})();

function big7Track(event, props) {
  const payload = Object.assign({ event: event }, props || {});
  (window.dataLayer = window.dataLayer || []).push(payload);
}
async function submitForm(e) {
  e.preventDefault();
  const form = e.target;
  if (document.documentElement?.hasAttribute('data-preview')) {
    const status = form.querySelector('.form-note');
    const brief = form.querySelector('#brief-review');
    const service = form.querySelector('input[name="projectType"]:checked');
    const rows = [
      ['Service', service?.closest('label').textContent.trim()],
      ['Contact', form.elements.name.value],
      ['Email', form.elements.email.value],
      ['Phone', form.elements.phone.value],
      ['Company', form.elements.company.value],
      ['Project location', form.elements.location.value],
      ['Scope and timing', form.elements.message.value]
    ];
    const content = rows.filter(([, value]) => value?.trim())
      .map(([label, value]) => label + ': ' + value.trim()).join('\n');
    brief.querySelector('.brief-text').textContent = content;
    brief.hidden = false;
    brief.querySelector('h3').focus();
    status.textContent = 'Your project brief is ready. Nothing has been sent.';
    status.dataset.state = 'preview';
    return;
  }

}
(function () {
  const INTENT_TO_TYPE = {
    __proto__: null,
    'service:enterprise-framing': 'commercial-new',
    'service:commercial-new': 'commercial-new',
    'service:trades-only': 'trades-only',
    'service:drywall': 'trades-only',
    'service:tenant-improvement': 'tenant-improvement'
  };
  const PREFILL_MARK = '— Interested in: ';
  const SAFE_PARAM = /^[a-z0-9:_\-]{1,64}$/i;
  const safe = v => v && SAFE_PARAM.test(v) ? v : '';
  const form = document.querySelector('form.cform');
  function labelFor(el) {
    const title = el.querySelector('.service-title, .pf-title, .type-name');
    return ((title && title.textContent) || el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0,80);
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
    const review = form.querySelector('#brief-review');
    if (review) {
      form.addEventListener('input', () => {
        if (review.hidden) return;
        review.hidden = true;
        form.querySelector('.form-note').textContent = 'Review your updated brief before saving.';
      });
      review.querySelector('#save-brief').addEventListener('click', () => {
        const content = 'Big 7 Construction — consultation draft\n\n' + review.querySelector('.brief-text').textContent;
        const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = 'big7-commercial-project-brief.txt';
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      });
      form.querySelector('#formBtn').disabled = false;
    }
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
    // Bookmarked homepage inquiries predate the dedicated commercial form.
    if (BIG7_PAGE === 'home') {
      const oldResidential = ['residential-custom', 'residential-remodel', 'service:custom-home',
        'service:structural-repair', 'portfolio:custom-home-03', 'portfolio:residential-05', 'portfolio:structural-06'];
      if (oldResidential.includes(type) || oldResidential.includes(intent)) {
        window.location.replace('/Big7ConstructionWebSite/residential-construction/#home-repair');
        return;
      }
      if (Object.values(INTENT_TO_TYPE).includes(type) || INTENT_TO_TYPE[intent]) {
        const query = new URLSearchParams();
        if (type) query.set('type', type);
        if (intent) query.set('intent', intent);
        if (src) query.set('src', src);
        window.location.replace('/Big7ConstructionWebSite/commercial-industrial/?' + query + '#contact');
        return;
      }
    }
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
