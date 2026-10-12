"""In-memory browser fixture: same markup/CSS/JS, local assets embedded.
The execution container blocks HTTP and file navigation. This adapter renders
supplied HTML without bypassing that restriction. It is NOT a live-site probe.
"""
from pathlib import Path
from bs4 import BeautifulSoup
import base64
BASE=Path(__file__).resolve().parents[1]
SITE=BASE/'site'

def load(page, name='index.html', scripts=True):
    page.set_default_timeout(2000)
    soup=BeautifulSoup((SITE/name).read_text(),'html.parser')
    for link in list(soup.find_all('link')):
        if link.get('rel')!=['canonical']:link.decompose()
    for script in list(soup.find_all('script',src=True)):script.decompose()
    for img in soup.find_all('img'):
        p=SITE/img['src'].lstrip('/')
        img['src']='data:image/webp;base64,'+base64.b64encode(p.read_bytes()).decode()
        img.attrs.pop('loading',None)  # screenshots include below-fold pixels, all source images still tested separately
    page.set_content(str(soup),wait_until='domcontentloaded')
    if scripts:
        page.add_script_tag(content=(SITE/'big7.js').read_text())
        page.add_script_tag(content=(SITE/'theme.js').read_text())
    page.evaluate('Promise.all(Array.from(document.images).map(i=>i.decode().catch(()=>{})))')
    return page
