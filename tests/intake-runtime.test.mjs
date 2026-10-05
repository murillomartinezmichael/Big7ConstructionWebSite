import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Execute the actual browser script with synthetic DOM, clock and transport.
// No real endpoint can be called; no external packages or customer data required.
const source = readFileSync(new URL('../big7.js', import.meta.url), 'utf8');
const receipt = (body = { next: '/thanks' }, overrides = {}) => ({
  ok: true, status: 200, redirected: false,
  headers: { get: () => 'application/json; charset=utf-8' },
  json: async () => body, ...overrides,
});
function fixture(primary = async () => receipt(), mirrorFailure = false) {
  const button = { textContent: 'Send request →', disabled: false, style: {} };
  const note = { textContent: 'Original note', setAttribute() {} };
  const input = { disabled: false, value: 'Synthetic project details' };
  const form = {
    action: 'https://primary.invalid/form',
    querySelectorAll: () => [input],
    querySelector: (selector) => selector === '#formBtn' ? button : selector === '.form-note' ? note : null,
    addEventListener() {}, setAttribute() {},
  };
  const calls = [];
  const timers = new Map();
  let timerId = 0;
  const context = vm.createContext({
    window: { location: { pathname: '/commercial-industrial', search: '' } },
    document: {
      getElementById: (id) => id === 'formBtn' ? button : null,
      querySelector: (selector) => selector === '.form-note' ? note : null,
      addEventListener() {},
    },
    URLSearchParams, AbortController,
    FormData: class {
      forEach(fn) { [['message', input.value], ['website', ''], ['_subject', 'Synthetic'], ['_replyto', 'test@example.invalid']].forEach(([k, v]) => fn(v, k)); }
    },
    setTimeout: (fn, delay) => { timers.set(++timerId, { fn, delay }); return timerId; },
    clearTimeout: (id) => timers.delete(id),
    fetch: async (url, options) => {
      const kind = url === form.action ? 'primary' : 'mirror';
      calls.push({ kind, options });
      if (kind === 'primary') return primary(options);
      if (mirrorFailure) throw new Error('synthetic mirror outage');
      return receipt();
    },
  });
  vm.runInContext(source, context, { filename: 'big7.js' });
  const submit = () => context.submitForm({ target: form, preventDefault() {} });
  return { submit, button, input, note, calls, timers };
}

test('pending and accepted submissions never dispatch duplicate primary or mirror requests', async () => {
  let resolve;
  const pending = new Promise((done) => { resolve = done; });
  const f = fixture(() => pending);
  const first = f.submit();
  const duplicate = f.submit();
  const pendingCount = f.calls.length;
  resolve(receipt());
  await Promise.all([first, duplicate]);
  assert.equal(pendingCount, 2, 'one primary and one mirror while pending');
  await f.submit();
  assert.equal(f.calls.length, 2, 'accepted form remains locked');
  assert.equal(f.button.disabled, true);
  assert.equal(f.input.disabled, true);
});

for (const [name, response] of [
  ['HTTP error', receipt({}, { ok: false, status: 503 })],
  ['redirect', receipt(undefined, { redirected: true })],
  ['HTML success', receipt(undefined, { headers: { get: () => 'text/html' } })],
  ['empty JSON', receipt({})],
  ['JSON error', receipt({ error: 'Rejected', next: '/thanks' })],
  ['JSON errors', receipt({ errors: [{ message: 'Rejected' }], next: '/thanks' })],
  ['JSON array', receipt([])],
  ['null JSON', receipt(null)],
  ['malformed JSON', receipt(undefined, { json: async () => { throw new SyntaxError('invalid'); } })],
]) {
  test(`${name} preserves fields, makes no success claim, and allows deliberate retry`, async () => {
    let attempts = 0;
    const f = fixture(async () => ++attempts === 1 ? response : receipt());
    await f.submit();
    assert.equal(f.input.value, 'Synthetic project details');
    assert.equal(f.input.disabled, false);
    assert.equal(f.button.disabled, false);
    assert.doesNotMatch(f.button.textContent, /received/);
    assert.match(f.note.textContent, /could not confirm/i);
    await f.submit();
    assert.equal(attempts, 2);
    assert.match(f.button.textContent, /received/);
    assert.equal(f.timers.size, 0);
  });
}

test('mirror outage cannot fail an accepted primary delivery; mirror excludes internal fields', async () => {
  const f = fixture(undefined, true);
  await f.submit();
  assert.match(f.button.textContent, /received/);
  const payload = f.calls.find((call) => call.kind === 'mirror').options.body;
  assert.equal(payload.get('message'), f.input.value);
  for (const key of ['website', '_subject', '_replyto']) assert.equal(payload.has(key), false);
});

test('transport rejection preserves the request without automatic retry', async () => {
  const f = fixture(async () => { throw new Error('synthetic offline'); });
  await f.submit();
  assert.equal(f.calls.length, 2);
  assert.equal(f.button.disabled, false);
  assert.equal(f.input.disabled, false);
  assert.match(f.note.textContent, /could not confirm/i);
  assert.equal(f.timers.size, 0);
});

test('bounded timeout aborts stalled primary delivery without claiming it was unsent', async () => {
  const f = fixture(({ signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new Error('synthetic timeout')), { once: true });
  }));
  const run = f.submit();
  assert.equal(f.timers.size, 1);
  const timer = [...f.timers.values()][0];
  assert.equal(timer.delay, 30000);
  timer.fn();
  await run;
  assert.equal(f.button.disabled, false);
  assert.equal(f.input.disabled, false);
  assert.match(f.note.textContent, /could not confirm/i);
  assert.doesNotMatch(f.note.textContent, /nothing.*sent|not sent/i);
  assert.equal(f.calls.length, 2);
  assert.equal(f.timers.size, 0);
});
