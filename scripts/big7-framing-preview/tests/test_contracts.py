"""Candidate contracts only; these are not the untouched repository's Makefile suites."""
from pathlib import Path
import hashlib, importlib.util, http.client, json, re, subprocess, sys, threading, unittest
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup
from PIL import Image
BASE=Path(__file__).resolve().parents[1]
SITE=BASE/'site'
ROUTES={'/':'index.html','/commercial-industrial':'commercial-industrial.html','/residential-construction':'residential-construction.html','/south-fulton-distribution':'south-fulton-distribution.html','/accessibility':'accessibility.html','/404':'404.html'}

def errors(text):
    s=BeautifulSoup(text,'html.parser');e=[]
    if len(s.find_all('h1'))!=1:e.append('one-h1')
    if not s.html or s.html.get('lang')!='en':e.append('language')
    ids=[a['id'] for a in s.select('[id]')]
    if len(ids)!=len(set(ids)):e.append('duplicate-id')
    if not s.select_one('main#main') or not s.select_one('a.skip-link[href="#main"]'):e.append('landmarks')
    if s.select('a[href^="tel:"]') or re.search(r'555[- )]*700|5557000007',text):e.append('placeholder-phone')
    if not s.html.has_attr('data-preview'):e.append('preview-gate')
    for f in s.select('form'):
        if f.get('action')!='/__preview-intake':e.append('preview-action')
        if f.get('data-live-action')!='https://formspree.io/f/xykabwog':e.append('endpoint-identity')
        for name in ['name','email','phone']:
            v=f.select_one(f'input[name="{name}"]')
            if not v or not v.has_attr('required'):e.append('required-'+name)
        if not f.select_one('input[name="projectType"][required]'):e.append('required-service')
    for im in s.find_all('img'):
        if not im.get('alt') or 'AI-generated' not in im['alt']:e.append('image-provenance')
        if not im.has_attr('width') or not im.has_attr('height'):e.append('image-dimensions')
    if s.find('img') and 'AI-generated illustration' not in s.get_text(' '):e.append('visible-disclosure')
    return e

class ContentTests(unittest.TestCase):
    def setUp(self):self.pages={n:(SITE/n).read_text() for n in ROUTES.values()}
    def test_six_complete_pages(self):self.assertEqual(len(self.pages),6)
    def test_page_contracts(self):
        for n,t in self.pages.items():self.assertEqual(errors(t),[],n)
    def test_distinct_titles_descriptions(self):
        pages=[BeautifulSoup(t,'html.parser') for t in self.pages.values()]
        self.assertEqual(len({s.title.text for s in pages}),6)
        self.assertEqual(len({s.find('meta',attrs={'name':'description'})['content'] for s in pages}),6)
        for s in pages:self.assertTrue(40<=len(s.find('meta',attrs={'name':'description'})['content'])<=220)
    def test_canonical_routes(self):
        for route,n in ROUTES.items():
            s=BeautifulSoup(self.pages[n],'html.parser');link=s.find('link',rel='canonical')
            if route=='/404':self.assertIsNone(link)
            else:self.assertEqual(link['href'],'https://big7construction.com'+route)
    def test_all_internal_links_resolve(self):
        for n,t in self.pages.items():
            soup=BeautifulSoup(t,'html.parser')
            for a in soup.find_all('a',href=True):
                u=urlsplit(a['href'])
                if u.scheme:continue
                target=ROUTES.get(u.path) if u.path else n
                self.assertIsNotNone(target,(n,a['href']))
                if u.fragment:self.assertIsNotNone(BeautifulSoup(self.pages[target],'html.parser').find(id=unquote(u.fragment)),(n,a['href']))
    def test_no_unconfirmed_claims(self):
        pattern=r'licensed|bonded|insured|500\+|24/7|5.star|guaranteed|within 48 hours|every trade in.house|\$[0-9]'
        for n,t in self.pages.items():
            soup=BeautifulSoup(t,'html.parser')
            self.assertIsNone(re.search(pattern,soup.get_text(' '),re.I),n)
    def test_no_company_founding_claim(self):
        for t in self.pages.values():
            self.assertNotIn('foundingDate',t)
            self.assertNotIn('established in',t.lower())
        self.assertIn('Years of industry experience',self.pages['index.html'])
    def test_shared_inline_css_and_font_contract(self):
        for t in self.pages.values():
            soup=BeautifulSoup(t,'html.parser')
            self.assertEqual(soup.style.string,(BASE/'src/design.css').read_text())
            fontlinks=[x['href'] for x in soup.find_all('link',href=True) if x['href'].startswith('https://fonts.googleapis.com/css2')]
            self.assertEqual(len(fontlinks),3);self.assertEqual(len(set(fontlinks)),1)
    def test_assets_and_actual_dimensions(self):
        for t in self.pages.values():
            for im in BeautifulSoup(t,'html.parser').find_all('img'):
                p=SITE/im['src'].lstrip('/');self.assertTrue(p.is_file())
                with Image.open(p) as actual:self.assertEqual(actual.size,(int(im['width']),int(im['height'])))
    def test_hero_preload_and_not_lazy(self):
        for n in ['index.html','commercial-industrial.html','residential-construction.html']:
            s=BeautifulSoup(self.pages[n],'html.parser');im=s.select_one('.hero img')
            self.assertEqual(im.get('fetchpriority'),'high');self.assertNotEqual(im.get('loading'),'lazy')
            self.assertEqual(s.find('link',attrs={'as':'image'})['href'],im['src'])
    def test_nonhero_images_lazy(self):
        for t in self.pages.values():
            for im in BeautifulSoup(t,'html.parser').select('img:not(.hero img)'):
                self.assertEqual(im.get('loading'),'lazy');self.assertEqual(im.get('decoding'),'async')
    def test_schemas_are_truthful_and_parse(self):
        for n,t in self.pages.items():
            for tag in BeautifulSoup(t,'html.parser').find_all('script',type='application/ld+json'):
                obj=json.loads(tag.string);self.assertIn('@graph',obj)
                flat=json.dumps(obj).lower()
                for forbidden in ['aggregaterating','reviewrating','telephone','foundingdate']:self.assertNotIn(forbidden,flat)
    def test_faq_visible_schema_match(self):
        for t in self.pages.values():
            s=BeautifulSoup(t,'html.parser');visible=[x.text for x in s.select('.faq-list summary')]
            graph=[json.loads(v.string) for v in s.find_all('script',type='application/ld+json')]
            schemaqs=[q['name'] for g in graph for o in g['@graph'] if o.get('@type')=='FAQPage' for q in o['mainEntity']]
            self.assertEqual(visible,schemaqs)
    def test_form_contract_and_no_home_form(self):
        self.assertEqual(len(BeautifulSoup(self.pages['index.html'],'html.parser').find_all('form')),0)
        for n in ['commercial-industrial.html','residential-construction.html']:
            s=BeautifulSoup(self.pages[n],'html.parser');f=s.select_one('form.cform')
            self.assertEqual(f['method'],'POST');self.assertEqual(f['onsubmit'],'submitForm(event)')
            for name in ['_subject','_replyto','source','projectType','name','email','phone','message','website']:
                self.assertIsNotNone(f.find(attrs={'name':name}),name)
            self.assertIsNotNone(f.select_one('#formBtn'));self.assertIsNotNone(f.select_one('.form-note[role="status"]'))
    def test_contact_cta_intents(self):
        for t in self.pages.values():
            for a in BeautifulSoup(t,'html.parser').select('a.btn'):self.assertTrue(a.get('data-intent'))
    def test_no_production_tracking_tag(self):
        for t in self.pages.values():
            s=BeautifulSoup(t,'html.parser')
            for tag in s.select('script[src]'):self.assertIn(tag['src'],['/big7.js','/theme.js'])
    def test_social_image_exists(self):
        with Image.open(SITE/'images/og-card.png') as im:self.assertEqual(im.size,(1200,630))
    def test_image_budget(self):
        total=sum(p.stat().st_size for p in (SITE/'images').iterdir());self.assertLess(total,220000)
    def test_javascript_syntax(self):
        for name in ['big7.js','theme.js']:self.assertEqual(subprocess.run(['node','--check',str(SITE/name)],capture_output=True).returncode,0)
    def test_generator_is_reproducible(self):
        before={n:hashlib.sha256((SITE/n).read_bytes()).hexdigest() for n in self.pages}
        subprocess.run([sys.executable,str(BASE/'src/build_preview.py')],check=True,capture_output=True)
        self.assertEqual(before,{n:hashlib.sha256((SITE/n).read_bytes()).hexdigest() for n in self.pages})
    def test_mutations_are_rejected(self):
        home=self.pages['index.html'];form=self.pages['commercial-industrial.html']
        cases=[home.replace('<h1 id="hero-h1">','<h2 id="hero-h1">',1),home.replace('lang="en"','lang="zz"',1),home.replace('data-preview="true"','',1),home.replace('href="#main"','href="#missing"',1),home.replace('Commercial</a>','<span id="main">Duplicate</span></a>',1),home.replace('href="mailto:info@big7construction.com"','href="tel:5557000007"',1),form.replace('action="/__preview-intake"','action="https://example.invalid/send"',1),form.replace('name="name" required','name="name"',1),home.replace('width="646" height="417"','',1),home.replace('; AI-generated, not a Big 7 project','',1)]
        for i,mutant in enumerate(cases):self.assertTrue(errors(mutant),i)

class PreviewServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('big7_preview',BASE/'preview.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        cls.server=m.ThreadingHTTPServer(('127.0.0.1',0),m.PreviewHandler)
        cls.port=cls.server.server_address[1];cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,method='GET'):
        c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3);c.request(method,path);r=c.getresponse();v=(r.status,dict(r.getheaders()),r.read());c.close();return v
    def test_clean_routes(self):
        for route in ROUTES:self.assertEqual(self.request(route)[0],404 if route=='/404' else 200,route)
    def test_real_404(self):
        status,_,body=self.request('/not-a-real-page');self.assertEqual(status,404);self.assertIn('That page isn’t here.'.encode(),body)
    def test_legacy_redirects_keep_queries(self):
        for source,target in [('/index.html','/'),('/commercial-industrial.html','/commercial-industrial'),('/residential-construction.html','/residential-construction'),('/accessibility.html','/accessibility')]:
            status,h,_=self.request(source+'?src=test&intent=service:drywall');self.assertEqual(status,301);self.assertEqual(h['Location'],target+'?src=test&intent=service:drywall')
    def test_home_repair_redirect_preserves_anchor_and_query(self):
        for path in ['/home-repair','/home-repair.html']:
            status,h,_=self.request(path+'?src=example');self.assertEqual(status,301);self.assertEqual(h['Location'],'/residential-construction?src=example#home-repair')
    def test_no_internal_files(self):
        for path in ['/../README.md','/%2e%2e/src/design.css','/src/design.css','/.git/config','/images/','/tests/test_contracts.py']:
            self.assertEqual(self.request(path)[0],404,path)
    def test_native_preview_post_cannot_send(self):self.assertEqual(self.request('/__preview-intake','POST')[0],405)
    def test_preview_security_headers(self):
        _,h,_=self.request('/');self.assertEqual(h['X-Robots-Tag'],'noindex, nofollow');self.assertEqual(h['X-Content-Type-Options'],'nosniff');self.assertEqual(h['X-Frame-Options'],'DENY')

if __name__=='__main__':unittest.main(verbosity=2)
