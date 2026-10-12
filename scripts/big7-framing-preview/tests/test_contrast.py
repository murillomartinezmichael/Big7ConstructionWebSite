from playwright.sync_api import sync_playwright
from browser_support import load,BASE
import json,re

def luminance(rgb):
    c=[v/255 for v in map(int,re.findall(r'\d+',rgb)[:3])]
    c=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]
    return sum(v*w for v,w in zip(c,[.2126,.7152,.0722]))

def contrast(a,b):
    lo,hi=sorted([luminance(a),luminance(b)]);return (hi+.05)/(lo+.05)

results=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    pairs=[('body','body'),('.hero-description','.hero'),('.hero-copy .eyebrow','.hero'),('.hero-credential span','.hero'),('.image-disclosure','.hero'),('.section-heading>p','body'),('.section-heading .eyebrow','body'),('.service-body>p','.service-card'),('.section-caption','body'),('.contact-band p','.contact-band'),('.primary-nav>a','.site-header'),('.hero .btn','.hero .btn')]
    for theme in ['light','dark']:
        pg=b.new_page(color_scheme=theme)
        load(pg)
        for foreground,background in pairs:
            fg=pg.locator(foreground).first.evaluate('(e)=>getComputedStyle(e).color')
            bg=pg.locator(background).first.evaluate('(e)=>getComputedStyle(e).backgroundColor')
            ratio=contrast(fg,bg)
            results.append({'theme':theme,'foreground':foreground,'background':background,'colors':[fg,bg],'ratio':round(ratio,3),'status':'PASS' if ratio>=4.5 else 'FAIL'})
        pg.close()
    b.close()
report={'scope':'24 selected rendered text/background pairs; does not cover every pixel or image-overlay text','checks':results,'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results)}
(BASE/'evidence/contrast-results.json').write_text(json.dumps(report,indent=2)+'\n')
for r in results:print(r['status'],r['theme'],r['foreground'],r['ratio'])
print('TOTAL',len(results),'PASS',report['passed'],'FAIL',report['failed'])
raise SystemExit(1 if report['failed'] else 0)
