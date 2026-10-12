"""Browser rendering + functional scenarios using the actual candidate markup/JS.
Network/file navigation is blocked in this execution environment. All test
pages are loaded in memory; external delivery is replaced with synthetic
fetch responses. This does not establish a live receipt, live routing, field
performance, production fonts, or a complete accessibility certification.
"""
import json, time, argparse
ap=argparse.ArgumentParser();ap.add_argument("--mode",choices=["all","layout","functions"],default="all");ap.add_argument("--start",type=int,default=0);ap.add_argument("--stop",type=int,default=999);ARGS=ap.parse_args();MODE=ARGS.mode;SEEN=0;SUFFIX=f"{MODE}-{ARGS.start}-{ARGS.stop}"
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import load, BASE
results=[]

def record(name, fn):
    global SEEN
    if MODE=="layout" and not name.startswith("layout:"):return
    if MODE=="functions" and name.startswith("layout:"):return
    idx=SEEN;SEEN+=1
    if not ARGS.start<=idx<ARGS.stop:return
    try:
        info=fn() or {}
        results.append({'name':name,'status':'PASS',**info})
    except Exception as e:
        results.append({'name':name,'status':'FAIL','error':str(e)})
    print(results[-1]['status'], name, results[-1].get('error',''),flush=True)
    (BASE/('evidence/browser-'+SUFFIX+'-progress.json')).write_text(json.dumps(results,indent=2))

def require(condition,msg):
    if not condition:raise AssertionError(msg)

FETCH_FIXTURE=r'''(scenario) => {
 document.documentElement.removeAttribute('data-preview');
 const form=document.querySelector('form.cform');
 form.action=form.dataset.liveAction;
 window.__deliveries=[];
 const originalTimeout=window.setTimeout.bind(window);
 window.setTimeout=(fn,ms,...args)=>originalTimeout(fn,ms===30000?50:ms,...args);
 window.fetch=(url,options)=>{
   const primary=String(url).startsWith('https://formspree.io/f/xykabwog');
   window.__deliveries.push({target:primary?'primary':'mirror',method:options.method,fields:Array.from(options.body.keys())});
   if(!primary) return scenario==='mirror-failure'?Promise.reject(new Error('synthetic mirror failure')):Promise.resolve({ok:true});
   if(scenario==='network-failure')return Promise.reject(new Error('synthetic network failure'));
   if(scenario==='timeout')return new Promise((_,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError'))));
   const json=scenario==='json-error'?{errors:['invalid']}:scenario==='array'?[]:scenario==='missing-next'?{ok:true}:scenario==='next-null'?{next:null}:scenario==='null'?null:{next:'/thanks'};
   return Promise.resolve({ok:!['http-400','http-500'].includes(scenario),redirected:scenario==='redirect',
     headers:new Headers({'content-type':scenario==='html-response'?'text/html':'application/json'}),
     json:()=>scenario==='malformed-json'?Promise.reject(new SyntaxError('synthetic bad JSON')):Promise.resolve(json)});
 };
}'''

def fill(page):
    page.locator('input[name="name"]').fill('Synthetic Test Person')
    page.locator('input[name="email"]').fill('synthetic@example.test')
    page.locator('input[name="phone"]').fill('2025550147')
    page.locator('input[name="projectType"]').first.check()
    page.locator('textarea[name="message"]').fill('Synthetic project for offline verification only.')

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    pages=['index.html','commercial-industrial.html','residential-construction.html','south-fulton-distribution.html','accessibility.html','404.html']
    for name in pages:
        for w,h in [(320,800),(390,844),(768,1024),(1440,1000)]:
            for theme in ['light','dark']:
                def run_layout(name=name,w=w,h=h,theme=theme):
                    page=browser.new_page(viewport={'width':w,'height':h},color_scheme=theme,device_scale_factor=1)
                    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                    try:
                        load(page,name)
                        width=page.evaluate('document.documentElement.scrollWidth')
                        require(width<=w+1,f'horizontal overflow {width}>{w}')
                        require(page.locator('h1').count()==1,'missing or duplicate h1')
                        require(page.locator('h1').is_visible(),'h1 invisible')
                        require(not errors,str(errors))
                        require(page.locator('a[href^="tel:"]').count()==0,'unapproved phone')
                        require(page.evaluate('Array.from(document.images).every(i=>i.naturalWidth>0)'),'image failed')
                        if w==1440 and theme=='light':
                            page.screenshot(path=str(BASE/'evidence'/f'{name[:-5]}-desktop.png'),full_page=True)
                        if w==390 and theme=='light':
                            page.screenshot(path=str(BASE/'evidence'/f'{name[:-5]}-mobile.png'),full_page=True)
                        if name=='index.html' and w==1440:
                            page.screenshot(path=str(BASE/'evidence'/f'homepage-first-screen-{theme}.png'))
                        return {'viewport':[w,h],'theme':theme,'scroll_width':width,'javascript_errors':errors}
                    finally:page.close()
                record(f'layout:{name}:{w}:{theme}',run_layout)
    def menu_test():
        page=browser.new_page(viewport={'width':390,'height':844})
        try:
            load(page)
            menu=page.locator('#primary-nav');toggle=page.locator('.menu-toggle')
            require(not menu.is_visible(),'mobile menu starts open')
            toggle.click();require(menu.is_visible(),'menu did not open')
            require(toggle.get_attribute('aria-expanded')=='true','state incorrect')
            page.keyboard.press('Escape')
            require(not menu.is_visible(),'Escape did not close')
            require(toggle.evaluate('(e)=>e===document.activeElement'),'focus was not restored')
            box=toggle.bounding_box();require(box['height']>=48,'menu hit area too small')
        finally:page.close()
    record('menu:open-Escape-focus-return',menu_test)
    def theme_test():
        page=browser.new_page(viewport={'width':390,'height':844},color_scheme='light')
        try:
            load(page);btn=page.locator('.theme-toggle')
            original=page.evaluate('getComputedStyle(document.body).backgroundColor')
            btn.click();require(page.locator('html').get_attribute('data-theme')=='dark','dark state not set')
            require(page.evaluate('getComputedStyle(document.body).backgroundColor')!=original,'palette did not change')
            require('light' in btn.get_attribute('aria-label'),'theme label incorrect')
            btn.click();require(page.locator('html').get_attribute('data-theme')=='light','light state not restored')
        finally:page.close()
    record('theme:toggle-in-memory-with-storage-unavailable',theme_test)
    def faq_test():
        page=browser.new_page()
        try:
            load(page);summary=page.locator('.faq-list summary').first
            summary.focus();page.keyboard.press('Enter')
            require(page.locator('.faq-list details').first.get_attribute('open') is not None,'keyboard FAQ did not open')
            page.keyboard.press('Enter');require(page.locator('.faq-list details').first.get_attribute('open') is None,'FAQ did not close')
        finally:page.close()
    record('faq:keyboard-disclosure',faq_test)
    def nojs_test():
        page=browser.new_page(java_script_enabled=False,viewport={'width':390,'height':844})
        try:
            load(page,'commercial-industrial.html',scripts=False)
            require(page.locator('#primary-nav').is_visible(),'navigation unavailable without JS')
            require(page.locator('form').get_attribute('action')=='/__preview-intake','native preview could send')
            require(page.locator('h1').is_visible(),'content depends on JS')
        finally:page.close()
    record('no-JavaScript:content-nav-safe-native-action',nojs_test)
    def reduced_test():
        page=browser.new_page(reduced_motion='reduce')
        try:
            load(page)
            require(page.evaluate('getComputedStyle(document.documentElement).scrollBehavior')=='auto','smooth scrolling not disabled')
            require(page.locator('.service-image img').first.evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s','transition remains')
        finally:page.close()
    record('motion:reduced-preference',reduced_test)
    def invalid_test():
        page=browser.new_page()
        try:
            load(page,'commercial-industrial.html');page.evaluate(FETCH_FIXTURE,'success')
            page.locator('#formBtn').click();require(page.evaluate('window.__deliveries.length')==0,'invalid form sent')
        finally:page.close()
    record('form:required-validation',invalid_test)
    def preview_test():
        page=browser.new_page()
        try:
            load(page,'commercial-industrial.html');fill(page)
            page.evaluate('()=>{window.__unexpected=0;window.fetch=()=>{window.__unexpected++;return Promise.reject(new Error("no network"))}}')
            page.locator('#formBtn').click()
            require(page.evaluate('window.__unexpected')==0,'preview sent request')
            require('nothing has been sent' in page.locator('.form-note').inner_text(),'preview receipt misleading')
        finally:page.close()
    record('form:preview-never-sends',preview_test)
    scenarios=['success','mirror-failure','http-400','http-500','html-response','json-error','array','null','missing-next','next-null','malformed-json','network-failure','redirect','timeout']
    for scenario in scenarios:
        def form_case(scenario=scenario):
            page=browser.new_page(viewport={'width':390,'height':844})
            try:
                load(page,'commercial-industrial.html');fill(page);page.evaluate(FETCH_FIXTURE,scenario)
                page.locator('#formBtn').click();page.wait_for_timeout(90)
                status=page.locator('.form-note').get_attribute('data-state')
                success=scenario in ('success','mirror-failure')
                require(status==('success' if success else 'error'),f'wrong state {status}')
                require(page.locator('input[name="name"]').input_value()=='Synthetic Test Person','input lost')
                require(page.locator('#formBtn').is_disabled()==success,'button state incorrect')
                deliveries=page.evaluate('window.__deliveries')
                require(len([r for r in deliveries if r['target']=='primary'])==1,'wrong primary count')
                dl=page.evaluate('JSON.stringify(window.dataLayer)')
                for secret in ['Synthetic Test Person','synthetic@example.test','2025550147','Synthetic project for offline']:
                    require(secret not in dl,'PII in telemetry')
                require(('intake_confirmed' in dl)==success,'receipt analytics incorrect')
                require('555' not in page.locator('.form-note').inner_text(),'placeholder phone in state')
                if not success:require('may already have arrived' in page.locator('.form-note').inner_text(),'ambiguous receipt not explained')
                if scenario in ('success','network-failure'):
                    page.locator('form').scroll_into_view_if_needed()
                    page.screenshot(path=str(BASE/'evidence'/f'form-{scenario}.png'))
                return {'scenario':scenario,'state':status,'primary_requests':1,'network':'synthetic; no live request'}
            finally:page.close()
        record('delivery:'+scenario,form_case)
    def duplicate_test():
        page=browser.new_page()
        try:
            load(page,'commercial-industrial.html');fill(page);page.evaluate(FETCH_FIXTURE,'success')
            page.evaluate('''()=>{const f=document.querySelector('form');f.requestSubmit();f.requestSubmit();}''')
            page.wait_for_timeout(60)
            require(page.evaluate('window.__deliveries.filter(x=>x.target==="primary").length')==1,'duplicate primary send')
            require(page.evaluate('window.dataLayer.filter(x=>x.event==="intake_confirmed").length')==1,'duplicate confirmed receipt')
        finally:page.close()
    record('delivery:reentrant-duplicate-guard',duplicate_test)
    def service_prefill():
        page=browser.new_page()
        try:
            load(page,'commercial-industrial.html')
            page.evaluate("document.addEventListener('click',e=>{if(e.target.closest('[data-intent]'))e.preventDefault()})")
            page.locator('.scope-card [data-intent="service:drywall"]').click()
            require(page.locator('input[value="trades-only"]').is_checked(),'drywall prefill wrong')
            require('Drywall' in page.locator('textarea').input_value(),'missing description')
            page.locator('textarea').fill('Keep these typed details.')
            page.locator('.scope-card [data-intent="service:enterprise-framing"]').click()
            require(page.locator('textarea').input_value()=='Keep these typed details.','prefill destroyed edits')
            require(page.locator('input[value="trades-only"]').is_checked(),'prefill overwrote manual service selection')
        finally:page.close()
    record('prefill:service-choice-and-preserved-edits',service_prefill)
    def honeypot():
        page=browser.new_page()
        try:
            load(page,'residential-construction.html');fill(page);page.evaluate(FETCH_FIXTURE,'success')
            page.locator('input[name="website"]').evaluate('(e)=>e.value="synthetic-spam"')
            page.locator('#formBtn').click();require(page.evaluate('window.__deliveries.length')==0,'honeypot submitted')
        finally:page.close()
    record('form:honeypot-no-delivery',honeypot)
    def two_hundred_zoom():
        page=browser.new_page(viewport={'width':720,'height':500})
        try:
            load(page,'commercial-industrial.html')
            require(page.evaluate('document.documentElement.scrollWidth')<=720,'effective 200% reflow overflow')
            return {'method':'720 CSS px effective viewport corresponding to 1440px at 200%; not browser zoom automation'}
        finally:page.close()
    record('reflow:effective-200-percent-width',two_hundred_zoom)
    browser_version=browser.version
    browser.close()
report={'mode':'In-memory Chromium DOM rendering; local images embedded; default fallback fonts; synthetic fetch responses.',
        'browser':browser_version,'total':len(results),'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results),'cases':results}
(BASE/('evidence/browser-'+SUFFIX+'-results.json')).write_text(json.dumps(report,indent=2)+'\n')
for result in results:print(result['status'],result['name'],result.get('error',''))
print(f"TOTAL {report['total']} PASS {report['passed']} FAIL {report['failed']}")
raise SystemExit(1 if report['failed'] else 0)
