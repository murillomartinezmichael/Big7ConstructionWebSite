from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import load, BASE
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for name,w,h in [('desktop',1440,1000),('mobile',390,844)]:
        page=browser.new_page(viewport={'width':w,'height':h},device_scale_factor=1,color_scheme='light')
        load(page)
        page.screenshot(path=str(BASE/'evidence'/f'homepage-{name}.png'),full_page=True)
        if name=='desktop':page.screenshot(path=str(BASE/'evidence/homepage-first-screen.png'))
        print(name,page.title(),page.locator('h1').inner_text(),page.evaluate('document.documentElement.scrollWidth'),w)
        page.close()
    browser.close()
