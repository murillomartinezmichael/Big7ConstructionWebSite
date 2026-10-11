import assert from 'node:assert/strict';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { dirname, extname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Reuse an explicitly supplied existing Puppeteer installation. No installer,
// provider traffic, real submissions or application server is involved.
const [packagePath, chromePath, outputPath] = process.argv.slice(2);
const deliveryOnly = process.argv.includes('--delivery-only');
if (!packagePath || !chromePath || !outputPath) throw new Error('Usage: node tests/intake-browser.mjs <existing-package.json> <chrome.exe> <evidence-directory>');
const require = createRequire(resolve(packagePath));
const puppeteer = require('puppeteer-core');
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8');
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = resolve(outputPath);
await mkdir(output, { recursive: true });
const origin = 'https://big7.fixture.invalid';
const routes = ['index', 'commercial-industrial', 'residential-construction', 'south-fulton-distribution', 'accessibility', '404'];
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.pdf': 'application/pdf' };
const browser = await puppeteer.launch({ executablePath: chromePath, headless: true });
const proof = { mode: deliveryOnly ? 'delivery-only' : 'all', sourceSha256: createHash('sha256').update(await readFile(join(root, 'big7.js'))).digest('hex'), browser: await browser.version(), network: 'All requests intercepted; primary and mirror responses synthetic; third-party assets blocked', pages: [], delivery: [] };

async function fixture() {
  const page = await browser.newPage();
  const state = { mode: 'fail', primary: 0, mirror: 0, release: null, pageErrors: [], blockedOrigins: new Set() };
  page.on('pageerror', (error) => state.pageErrors.push(error.message));
  await page.setRequestInterception(true);
  page.on('request', async (request) => {
    const url = new URL(request.url());
    const response = (status, contentType, body) => request.respond({ status, contentType, body, headers: { 'access-control-allow-origin': origin } });
    try {
      if (url.origin === 'https://formspree.io' && request.method() === 'POST') {
        state.primary++;
        if (state.mode === 'pending') await new Promise((done) => { state.release = done; });
        if (state.mode === 'fail') return await response(503, 'application/json', '{"error":"synthetic outage"}');
        if (state.mode === 'html') return await response(200, 'text/html', '<html>Unexpected response</html>');
        return await response(200, 'application/json', '{"next":"/thanks"}');
      }
      if (request.method() === 'POST') {
        state.mirror++;
        return await response(200, 'application/json', '{}');
      }
      if (url.origin !== origin) {
        state.blockedOrigins.add(url.origin);
        return await request.abort('blockedbyclient');
      }
      let path = decodeURIComponent(url.pathname).replace(/^\//, '');
      if (path === '') path = 'index.html';
      if (routes.includes(path)) path += '.html';
      const allowed = routes.some((route) => path === route + '.html') || ['big7.js', 'theme.js', 'theme.css', 'favicon.ico'].includes(path) || /^images\/[a-zA-Z0-9_./-]+\.(png|webp|jpe?g|svg|ico)$/.test(path) || path === 'docs/big7-capability-statement.pdf';
      if (!allowed || path.includes('..') || path.includes('\\')) return await response(404, 'text/plain', 'fixture denied');
      return await response(200, mime[extname(path)] || 'application/octet-stream', await readFile(join(root, path)));
    } catch {
      if (!request.isInterceptResolutionHandled()) await response(404, 'text/plain', 'fixture missing');
    }
  });
  return { page, state };
}

try {
  for (const width of [320, 375, 1440]) {
    for (const route of deliveryOnly ? [] : routes) {
      for (const theme of ['light', 'dark']) {
      const { page, state } = await fixture();
      await page.setViewport({ width, height: 900 });
      await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: theme }]);
      await page.goto(`${origin}/${route === 'index' ? '' : route}`, { waitUntil: 'networkidle0' });
      await page.addScriptTag({ content: axe });
      const result = await page.evaluate(async () => {
        const a11y = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } });
        const overflowElements = [...document.querySelectorAll('body *')].map((element) => {
          const rect = element.getBoundingClientRect();
          return { tag: element.tagName, id: element.id, className: element.className, right: Math.round(rect.right), left: Math.round(rect.left), width: Math.round(rect.width) };
        }).filter((e) => e.width > 0 && (e.right > innerWidth + 1 || e.left < -1)).slice(0, 25);
        return { overflow: document.documentElement.scrollWidth > innerWidth, overflowElements, violations: a11y.violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.map((n) => ({ target: n.target, summary: n.failureSummary })) })) };
      });
      const screenshot = `${route}-${width}-${theme}.png`;
      await page.screenshot({ path: join(output, screenshot), fullPage: true });
      proof.pages.push({ route, width, theme, ...result, screenshot, pageErrors: state.pageErrors, blockedOrigins: [...state.blockedOrigins] });
      await page.close();
      }
    }
    for (const route of ['commercial-industrial', 'residential-construction']) {
      const { page, state } = await fixture();
      await page.setViewport({ width, height: 900 });
      await page.goto(`${origin}/${route}?type=${route === 'commercial-industrial' ? 'commercial-new' : 'residential-custom'}&src=synthetic-test`, { waitUntil: 'networkidle0' });
      await page.evaluate(() => {
        const form = document.querySelector('form.cform');
        for (const [name, value] of Object.entries({ name: 'Synthetic Test', email: 'test@example.invalid', phone: '2025550123', message: 'Synthetic project details' })) form.elements.namedItem(name).value = value;
      });
      const submit = () => page.evaluate(() => document.querySelector('form.cform').requestSubmit());
      await submit();
      await page.waitForFunction(() => document.querySelector('.form-note').textContent.includes('could not confirm'));
      assert.equal(await page.$eval('.form-note', (e) => e.getAttribute('role')), 'status');
      assert.equal(state.primary, 1);
      assert.equal(await page.$eval('textarea[name="message"]', (e) => e.value), 'Synthetic project details');
      state.mode = 'html';
      await submit();
      await page.waitForFunction(() => !document.getElementById('formBtn').disabled);
      assert.equal(state.primary, 2);
      assert.equal(await page.$eval('textarea[name="message"]', (e) => e.disabled), false);
      state.mode = 'pending';
      await submit();
      await page.waitForFunction(() => document.getElementById('formBtn').disabled);
      for (let i = 0; i < 100 && !state.release; i++) await new Promise((done) => setTimeout(done, 10));
      assert.equal(typeof state.release, 'function');
      await page.evaluate(() => {
        const form = document.querySelector('form.cform');
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      });
      assert.equal(state.primary, 3);
      assert.equal(state.mirror, 3);
      state.mode = 'success';
      state.release();
      await page.waitForFunction(() => document.getElementById('formBtn').textContent.includes('received'));
      await page.evaluate(() => document.querySelector('form.cform').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
      assert.equal(state.primary, 3);
      assert.equal(state.mirror, 3);
      assert.deepEqual(state.pageErrors, []);
      proof.delivery.push({ route, width, checks: ['503 retains input', 'HTML200 not accepted', 'pending duplicate blocked', 'accepted duplicate blocked', 'one mirror per attempt'], primary: state.primary, mirror: state.mirror });
      const form = await page.$('form.cform');
      await form.screenshot({ path: join(output, `delivery-${route}-${width}.png`) });
      await page.close();
    }
  }
} finally {
  await browser.close();
  await writeFile(join(output, 'browser-proof.json'), JSON.stringify(proof, null, 2) + '\n');
}
const failedPages = proof.pages.filter((p) => p.overflow || p.violations.length || p.pageErrors.length);
console.log(JSON.stringify({ pages: proof.pages.length, delivery: proof.delivery.length, failedPages: failedPages.map((p) => ({ route: p.route, width: p.width, theme: p.theme, overflow: p.overflow, violations: p.violations.map((v) => v.id), errors: p.pageErrors })) }));
assert.equal(failedPages.length, 0, 'See browser-proof.json for exact accessibility/layout findings');
assert.equal(proof.pages.length, deliveryOnly ? 0 : 36);
assert.equal(proof.delivery.length, 6);
