#!/usr/bin/env python3
"""Emit a static, no-build-at-runtime Big 7 design candidate. Preview only.
The existing public routes and intake field names are retained. Publication
requires integration review; this generator cannot publish or enable delivery.
"""
from pathlib import Path
import html, json
BASE = Path(__file__).resolve().parents[1]
SITE = BASE / 'site'
CSS = (BASE / 'src/design.css').read_text()
ORIGIN = 'https://big7construction.com'
FONTS = 'https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=Fraunces:opsz,wght@9..144,400;9..144,500&family=Inter:wght@400;500;600;700&display=swap'
ARROW = '<svg class="arrow" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 12h15M13 5l7 7-7 7" stroke="currentColor" stroke-width="1.5"/></svg>'
CHECK = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m5 12 4 4L19 6" stroke="currentColor" stroke-width="1.7"/></svg>'
MOON = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20 15.2A8.4 8.4 0 0 1 8.8 4 8.4 8.4 0 1 0 20 15.2Z" stroke="currentColor" stroke-width="1.5"/></svg>'
MENU = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="1.5"/></svg>'
WORDMARK = '<a class="wordmark" href="/" aria-label="Big 7 Construction — home"><span class="brand-symbol" aria-hidden="true">7</span><span class="brand-type">BIG <em>7</em><small>CONSTRUCTION</small></span></a>'
DISCLOSURE = 'AI-generated illustration — not a Big 7 project photograph.'


def button(text, href, intent, extra='', label=None):
    return f'<a class="btn {extra}" href="{html.escape(href, quote=True)}" data-intent="{intent}"'+(f' aria-label="{html.escape(label, quote=True)}"' if label else '')+f'>{text}{ARROW}</a>'


def textlink(text, href, intent, label=None):
    return f'<a class="text-link" href="{html.escape(href, quote=True)}" data-intent="{intent}"'+(f' aria-label="{html.escape(label,quote=True)}"' if label else '')+f'>{text}{ARROW}</a>'


def image(name, eager=False):
    size={'framing':(646,417),'residential':(479,183),'repairs':(486,180)}[name]
    alt={'framing':'Illustrative timber framing with daylight falling across the structure',
         'residential':'Illustrative home exterior with warm timber finishes',
         'repairs':'Illustrative woodworking tools and timber on a workbench'}[name]
    flags='fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return f'<img src="/images/concept-{name}.webp" width="{size[0]}" height="{size[1]}" alt="{alt}; AI-generated, not a Big 7 project" {flags} />'


def header(active=''):
    return f'''<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap header-inner">{WORDMARK}
<nav class="primary-nav" id="primary-nav" aria-label="Main navigation">
<a href="/commercial-industrial" {'aria-current="page"' if active=='commercial' else ''}>Commercial</a>
<a href="/residential-construction" {'aria-current="page"' if active=='residential' else ''}>Residential</a>
<a href="/residential-construction#home-repair">Home repairs</a><a href="/#why-big7">Why Big 7</a>
{button('Request an Estimate','#contact' if active in ('home','commercial','residential') else '/#contact','bid:header')}
</nav><div class="header-tools"><button class="theme-toggle" type="button" aria-label="Switch color theme">{MOON}</button><button class="menu-toggle" type="button" aria-controls="primary-nav" aria-expanded="false">Menu {MENU}</button></div>
</div></header>'''


def footer(active=''):
    target='#contact' if active in ('home','commercial','residential') else '/#contact'
    return f'''<footer class="site-footer"><div class="wrap"><div class="footer-main"><div class="footer-brand">{WORDMARK}<p>Commercial framing, drywall and home repairs.<br>Hard work. Care in the details. Built right.</p></div>
<div class="footer-col"><h2>Explore our services</h2><a href="/commercial-industrial">Commercial framing &amp; drywall</a><a href="/residential-construction">Residential work</a><a href="/residential-construction#home-repair">Home repairs &amp; improvements</a></div>
<div class="footer-col"><h2>Let’s talk about the work</h2><p>Metro Atlanta, Georgia</p><a href="mailto:info@big7construction.com">info@big7construction.com</a><a href="{target}" data-intent="bid:footer">Request an estimate {ARROW}</a></div></div>
<div class="footer-bottom"><span>© <span id="year">2026</span> Big 7 Construction.</span><span>Built right. From the frame up.</span><a href="/accessibility">Accessibility</a></div></div></footer>
<nav class="sticky-estimate" aria-label="Quick estimate"><span>LET’S GET<br>TO WORK.</span>{button('Request an Estimate',target,'bid:sticky')}</nav>
<script defer src="/big7.js"></script><script defer src="/theme.js"></script>'''


def schema(path, title, description, service=None, faq=None):
    org={'@type':'GeneralContractor','@id':ORIGIN+'/#business','name':'Big 7 Construction','url':ORIGIN+'/',
         'description':'Commercial framing, drywall and home repairs in Metro Atlanta.',
         'email':'info@big7construction.com','areaServed':{'@type':'AdministrativeArea','name':'Metro Atlanta, Georgia'}}
    graph=[org]
    if service:
        graph += [{'@type':'Service','@id':ORIGIN+path+'#service','name':service,'url':ORIGIN+path,
                   'description':description,'provider':{'@id':ORIGIN+'/#business'},'areaServed':{'@type':'AdministrativeArea','name':'Metro Atlanta, Georgia'}},
                  {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':ORIGIN+'/'},{'@type':'ListItem','position':2,'name':title,'item':ORIGIN+path}]}]
    if faq:
        graph.append({'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in faq]})
    return '<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@graph':graph},ensure_ascii=False,indent=2)+'</script>'


def document(path, title, description, content, active='', hero_image=None, service=None, faq=None, noindex=False):
    canonical = '' if path=='/404' else f'<link rel="canonical" href="{ORIGIN+path}" />'
    preload = f'<link rel="preload" as="image" href="/images/concept-{hero_image}.webp" fetchpriority="high" />' if hero_image else ''
    # All delivered files are explicitly previews. A release cannot happen by
    # merely copying this folder: action and indexing gates remain visible.
    return f'''<!doctype html>
<html lang="en" data-preview="true"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description,quote=True)}" />
<meta name="robots" content="noindex, nofollow" /><meta name="theme-color" content="#121a1b" />{canonical}
<meta property="og:type" content="website" /><meta property="og:site_name" content="Big 7 Construction" />
<meta property="og:title" content="{html.escape(title,quote=True)}" /><meta property="og:description" content="{html.escape(description,quote=True)}" />
<meta property="og:url" content="{ORIGIN+path}" /><meta property="og:locale" content="en_US" />
<meta property="og:image" content="{ORIGIN}/images/og-card.png" /><meta property="og:image:width" content="1200" /><meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="Big 7 Construction — commercial framing, drywall and home repairs" />
<meta name="twitter:card" content="summary_large_image" /><meta name="twitter:title" content="{html.escape(title,quote=True)}" /><meta name="twitter:description" content="{html.escape(description,quote=True)}" />
<meta name="twitter:image" content="{ORIGIN}/images/og-card.png" /><meta name="twitter:image:alt" content="Big 7 Construction — commercial framing, drywall and home repairs" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' fill='%23121a1b'/%3E%3Ctext x='16' y='49' font-family='Arial' font-size='48' font-weight='bold' fill='%23ee9b71'%3E7%3C/text%3E%3C/svg%3E" />
<script>document.documentElement.classList.add('js');try{{var t=localStorage.getItem('big7-theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}}catch(_){{}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="preload" as="style" href="{FONTS}" /><link rel="stylesheet" href="{FONTS}" media="print" onload="this.media='all'" />
<noscript><link rel="stylesheet" href="{FONTS}" /></noscript>{preload}
{schema(path,title,description,service,faq) if path!='/404' else ''}
<style>{CSS}</style></head><body>{header(active)}<main id="main">{content}</main>{footer(active)}</body></html>'''


def hero(title, second, desc, asset='framing', eyebrow='Commercial framing · Drywall · Home repairs', active='home', image_label='The work starts here.', primary='Request an Estimate'):
    credential = '<div class="hero-credential"><strong>30+</strong><span>Years of industry experience.<br>A quality-first approach.</span></div>'
    return f'''<section class="hero {'lane-hero' if active!='home' else ''}" aria-labelledby="hero-h1"><div class="wrap hero-grid"><div class="hero-copy"><p class="eyebrow">{eyebrow}</p><h1 id="hero-h1">{title}<span>{second}</span></h1><p class="hero-description">{desc}</p><div class="button-row">{button(primary,'#contact','bid:hero')}{button('Explore Our Services','#services','service:explore','btn-outline')}</div>{credential}</div>
<figure class="hero-media"><div class="hero-photo">{image(asset,True)}<div class="image-index"><div><small>BIG 7 CONSTRUCTION</small><strong>{image_label}</strong></div><span class="corner" aria-hidden="true"></span></div></div><figcaption class="image-disclosure">{DISCLOSURE}</figcaption></figure></div>
<div class="hero-bottom"><div class="wrap"><span><i aria-hidden="true"></i> Commercial &amp; residential</span><span><i aria-hidden="true"></i> Quality before shortcuts</span><span><i aria-hidden="true"></i> Metro Atlanta, Georgia</span></div></div></section>'''


def contact_band():
    return f'''<section class="contact-band" id="contact" aria-labelledby="contact-h2"><div class="wrap"><div><p class="eyebrow">Let’s get to work</p><h2 id="contact-h2">Tell us what you’re building.<br>Or what needs fixing.</h2><p>Start with the kind of project you have in mind. We’ll take it from there, one conversation at a time.</p></div><div class="button-row">{button('Commercial estimate','/commercial-industrial#contact','bid:commercial')}{button('Home project or repair','/residential-construction#contact','bid:residential','btn-outline')}</div></div></section>'''


def standards():
    return f'''<section class="section standards" id="why-big7" aria-labelledby="standards-h2"><div class="wrap standards-grid"><div class="experience">30+<small>Years of industry<br>experience</small></div><div><p class="eyebrow accent">Why Big 7</p><h2 id="standards-h2">Hard work is the starting point.<br>Quality is the standard.</h2></div><div><p>Big 7 is built around a simple belief: the work should be done right, not rushed through. That means hardworking crews and care in the details.</p><ul class="standard-list"><li>{CHECK} Experience that informs the work</li><li>{CHECK} Quality before shortcuts</li><li>{CHECK} The same care for every project</li></ul></div></div></section>'''


def process():
    steps=[('Tell us about the work','Share your project type, location and what needs to be built, repaired or improved.'),('Talk through the details','Discuss the scope, site conditions and the crew support your project needs.'),('Agree on the next step','Confirm the approach, estimate and timing together before moving forward.')]
    return '<section class="section" aria-labelledby="process-h2"><div class="wrap"><div class="section-heading"><div><p class="eyebrow accent">A straightforward start</p><h2 id="process-h2">Good work starts with<br>a real conversation.</h2></div><p>No need to have every detail figured out. Tell us where you are with the project, and let’s discuss the next step.</p></div><div class="process-grid">'+''.join(f'<article class="process-step"><div class="step-num">0{i}</div><h3>{h}</h3><p>{p}</p></article>' for i,(h,p) in enumerate(steps,1))+'</div></div></section>'


def faq_block(items):
    return '<section class="section standards" aria-labelledby="faq-h2"><div class="wrap faq-grid"><div><p class="eyebrow accent">Before we get started</p><h2 id="faq-h2">A few good<br>questions.</h2></div><div class="faq-list">'+''.join(f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q,a in items)+'</div></div></section>'

HOME_FAQ=[('What is Big 7’s main specialty?','Commercial wood framing and drywall are at the core of Big 7’s work. The company also provides crew support for other scopes, discussed project by project.'),('Do you also take on home repairs?','Yes. Home repairs and improvements are part of Big 7’s work. Share what needs attention so the scope can be discussed.'),('What does 30+ years mean?','It refers to industry experience behind the work, not a claim about when the company was founded.'),('Where do you work?','Big 7 serves Metro Atlanta. Include your project location in your request so availability can be discussed.')]


def home():
    cards=[('01','framing','Commercial framing<br>&amp; drywall','Wood framing and drywall are at the core of what we do. Tell us about your commercial project and the crew support you need.','Commercial services','/commercial-industrial','service:enterprise-framing','featured'),('02','repairs','Home repairs<br>&amp; improvements','Work around your home deserves the same care as a larger build. Tell us what needs fixing or improving.','Home repair services','/residential-construction#home-repair','service:structural-repair',''),('03','residential','Residential<br>work','Planning work on your home? Share the scope with Big 7, from the structure to the finishing details.','Residential services','/residential-construction','service:custom-home','')]
    services='''<section class="section" id="services" aria-labelledby="services-h2"><div class="wrap"><div class="section-heading"><div><p class="eyebrow accent">What we do</p><h2 id="services-h2">The right crew.<br>The right attention to the work.</h2></div><p>From commercial framing and drywall to repairs at home, Big 7 brings a quality-first approach to the work that matters to your project.</p></div><nav class="service-grid" aria-label="Buyer lanes">'''
    for n,asset,title,desc,label,href,intent,extra in cards:
        services+=f'<article class="service-card {extra}"><div class="service-image">{image(asset)}<span>{n} / BIG 7</span></div><div class="service-body"><h3 class="service-title">{title}</h3><p>{desc}</p>{textlink(label,href,intent)}</div></article>'
    services+='</nav><p class="section-caption">Service imagery is AI-generated illustration, not photography of completed Big 7 projects.</p></div></section>'
    homeband=f'''<section class="section" aria-labelledby="home-repair-h2"><div class="wrap residential-band"><figure class="residential-art">{image('repairs')}<figcaption>{DISCLOSURE}</figcaption></figure><div class="residential-copy"><p class="eyebrow">Not just commercial</p><h2 id="home-repair-h2">Your home deserves<br>work done right, too.</h2><p>Not every project is a commercial build. Big 7 also handles home repairs and improvements, bringing the same quality-first attitude to the place you live.</p>{button('Tell Us About Your Home Repair','/residential-construction?intent=service:structural-repair&src=home-repair-feature#contact','service:structural-repair','btn-outline','Home repairs and improvements')}</div></div></section>'''
    return document('/','Commercial Framing, Drywall & Home Repairs | Big 7 Construction','Big 7 Construction brings a quality-first approach to commercial wood framing, drywall and home repairs in Metro Atlanta. Tell us about your project.',hero('Built right.','From the frame up.','Commercial wood framing, drywall and home repairs—with hardworking crews and a commitment to getting the details right.')+services+standards()+homeband+process()+faq_block(HOME_FAQ)+contact_band(),'home','framing',faq=HOME_FAQ)


def form(lane):
    commercial=lane=='commercial'
    name='commercial-industrial' if commercial else 'residential-construction'
    options=[('commercial-new','Wood framing'),('trades-only','Drywall'),('tenant-improvement','Other crew support')] if commercial else [('residential-remodel','Home repairs & improvements'),('residential-custom','Residential project'),('trades-only','Other work')]
    radios=''.join(f'<label><input type="radio" name="projectType" value="{v}" {"required" if i==0 else ""} /><span class="type-name">{label}</span></label>' for i,(v,label) in enumerate(options))
    optional_company='<label class="field">Company / role <small>Optional</small><input name="company" autocomplete="organization" maxlength="160" /></label>' if commercial else ''
    return f'''<section class="section form-section" id="contact" aria-labelledby="contact-h2"><div class="wrap contact-grid"><div class="contact-copy"><p class="eyebrow accent">Request an estimate</p><h2 id="contact-h2">{'Tell us about the work.' if commercial else 'What needs your attention?'}</h2><p>{'Need commercial framing or drywall crews? Share your project location, scope and the support you need.' if commercial else 'Planning residential work or a home repair? Tell us what you have in mind so we can discuss the scope and next steps.'}</p><ol class="next-steps"><li>Share the basics.</li><li>Discuss the scope.</li><li>Agree on the next step.</li></ol><a class="contact-email" href="mailto:info@big7construction.com">info@big7construction.com</a></div>
<form class="cform" action="/__preview-intake" data-live-action="https://formspree.io/f/xykabwog" method="POST" onsubmit="submitForm(event)" aria-label="Request a {'commercial' if commercial else 'residential'} estimate">
<p class="preview-note">DESIGN PREVIEW · Submissions are disabled. Nothing will be sent.</p><p class="required-note">Fields marked * are required.</p>
<input type="hidden" name="_subject" value="New {'commercial' if commercial else 'residential'} bid via Big 7 Construction" /><input type="hidden" name="_replyto" value="" /><input type="hidden" name="source" value="{name}-page" />
<fieldset><legend>01 · Your project</legend><div class="type-grid">{radios}</div></fieldset>
<fieldset><legend>02 · Your details</legend><label class="field">Full name *<input name="name" required autocomplete="name" maxlength="120" /></label><div class="field-row"><label class="field">Email *<input type="email" name="email" required autocomplete="email" maxlength="254" /></label><label class="field">Phone *<input type="tel" name="phone" required autocomplete="tel" maxlength="40" /></label></div>{optional_company}<label class="field">Project location / city <small>Optional. A full street address is not needed.</small><input name="location" autocomplete="address-level2" maxlength="160" /></label></fieldset>
<fieldset><legend>03 · Tell us about it</legend><label class="field">Project details<textarea name="message" rows="5" maxlength="5000" placeholder="What needs to be built, repaired or improved? Include the scope and any timing you have in mind."></textarea></label></fieldset>
<div hidden aria-hidden="true"><label>Website (leave blank)<input type="text" name="website" tabindex="-1" autocomplete="off" /></label></div>
<button class="btn" type="submit" id="formBtn">Send Estimate Request {ARROW}</button>
<p class="form-note" role="status" aria-live="polite" aria-atomic="true">This is a preview. No request will be sent.</p>
<p class="privacy-note">When the live form is enabled, your contact details and project information go to Big 7 to respond to your request. Please do not include sensitive information.</p><noscript><p class="preview-note">JavaScript is off. Preview submissions are still disabled.</p></noscript>
</form></div></section>'''


def other_lanes():
    return '<nav class="other-lanes" aria-label="Other services"><div class="wrap"><span>Different kind of project?</span><a href="/commercial-industrial">Commercial framing &amp; drywall</a><a href="/residential-construction">Residential work</a><a href="/residential-construction#home-repair">Home repairs</a><a href="/">All services</a></div></nav>'


COM_FAQ=[('Can we contact Big 7 specifically for framing or drywall?','Yes. Commercial wood framing and drywall are the main specialties. Include the scope, project location and the crew support you need in your estimate request.'),('Can Big 7 help with other trades?','Big 7 has crews for additional work. Availability and the appropriate scope need to be discussed for each project; the website does not promise every trade for every job.'),('Do you promise a completion date online?','No. Scope, site conditions, coordination and timing are discussed for the individual project. Quality comes before shortcuts.'),('What should I include in an estimate request?','Start with your contact information, project location, type of work and a short description. Mention whether plans or other project information are available.')]
RES_FAQ=[('Do you handle repairs as well as residential projects?','Yes. Home repairs and improvements are part of Big 7’s work, alongside other residential projects.'),('What kinds of repairs should I ask about?','Describe what needs fixing, replacing or improving. Big 7 can discuss the scope and the appropriate crew support for the work.'),('Do I need a complete plan before reaching out?','No. Start with a description and your project location. You can discuss the details and what information is needed next.'),('Can I request emergency service through this form?','This is an estimate inquiry, not an emergency-response service. For an immediate safety emergency, contact the appropriate emergency service.')]


def commercial():
    scopes=[('01','Wood framing','Commercial wood framing is a core part of Big 7’s work. Talk with us about your plans, scope and the crew support needed on site.','Discuss framing','service:enterprise-framing'),('02','Drywall','From the frame to the next stage of the interior, discuss your drywall scope with a crew that takes care in the details.','Discuss drywall','service:drywall'),('03','Additional crew support','Have another scope in mind? Big 7 has crews for additional work. Availability and the right approach are discussed project by project.','Discuss your scope','service:tenant-improvement')]
    s='<section class="section" id="services" aria-labelledby="services-h2"><div class="wrap"><div class="section-heading"><div><p class="eyebrow accent">Our commercial focus</p><h2 id="services-h2">Framing is our foundation.<br>Quality carries through.</h2></div><p>For contractors, project managers and owners who need a hardworking crew—not another layer of sales talk.</p></div><div class="scope-list">'
    for n,title,desc,label,intent in scopes:
        s+=f'<article class="scope-card"><p class="eyebrow">{n} / COMMERCIAL</p><h3 class="service-title">{title}</h3><p>{desc}</p>{textlink(label,"#contact",intent,title)}</article>'
    s+='</div><p class="notice-box">Have plans or a scope of work? Mention them in your inquiry. Trade availability, site requirements and timing are discussed for your project.</p></div></section>'
    return document('/commercial-industrial','Commercial Wood Framing & Drywall | Big 7 Construction','Commercial wood framing and drywall crews in Metro Atlanta. Big 7 Construction brings hard work, industry experience and attention to the details.',hero('Strong frames.','Solid workmanship.','Commercial wood framing and drywall are at the core of what we do. Tell us about your project and the crew support you need.',eyebrow='Commercial wood framing · Drywall',active='commercial',image_label='From structure to finish.')+s+standards()+process()+faq_block(COM_FAQ)+form('commercial')+other_lanes(),'commercial','framing','Commercial Wood Framing & Drywall',COM_FAQ)


def residential():
    s=f'''<section class="section" id="services" aria-labelledby="services-h2"><div class="wrap"><div class="section-heading"><div><p class="eyebrow accent">Residential work</p><h2 id="services-h2">A home project.<br>Not a small detail.</h2></div><p>The place you live deserves care. From the structure to the finishing details, tell us what you’re planning so we can discuss the right approach.</p></div><div class="scope-list"><article class="scope-card"><p class="eyebrow">01 / REPAIR</p><h3 class="service-title">Fix what needs attention.</h3><p>Tell us what needs repairing or replacing at home. Share the condition and what you would like addressed.</p>{textlink('Talk about a repair','#contact','service:structural-repair','Home repairs')}</article><article class="scope-card"><p class="eyebrow">02 / IMPROVE</p><h3 class="service-title">Make your home work better.</h3><p>Discuss improvements and updates that matter to you. We’ll talk through the work and the next step.</p>{textlink('Discuss an improvement','#contact','service:structural-repair','Home improvements')}</article><article class="scope-card"><p class="eyebrow">03 / BUILD</p><h3 class="service-title">Plan the bigger picture.</h3><p>Have a larger residential project in mind? Tell us the scope, location and what you want to accomplish.</p>{textlink('Discuss a residential project','#contact','service:custom-home','Residential project')}</article></div></div></section>
<section class="section standards" id="home-repair" aria-labelledby="repair-h2"><div class="wrap residential-band"><figure class="residential-art">{image('repairs')}<figcaption>{DISCLOSURE}</figcaption></figure><div class="residential-copy"><p class="eyebrow">Home repairs &amp; improvements</p><h2 id="repair-h2">The work at home<br>matters just as much.</h2><p>Not every job is a commercial build. Big 7 also handles home repairs and improvements, with the same hardworking, quality-first attitude.</p>{button('Tell Us What Needs Fixing','#contact','service:structural-repair','btn-outline','Home repairs and improvements')}</div></div></section>'''
    return document('/residential-construction','Home Repairs & Residential Work | Big 7 Construction','Home repairs, improvements and residential projects in Metro Atlanta. Talk with Big 7 Construction about the work your home needs.',hero('Your home.','Our full attention.','Home repairs, improvements and residential work—with the same commitment to getting the details right.',asset='repairs',eyebrow='Residential work · Home repairs',active='residential',image_label='Care in every detail.')+s+process()+faq_block(RES_FAQ)+form('residential')+other_lanes(),'residential','repairs','Home Repairs & Residential Work',RES_FAQ)


def accessibility():
    text='''<div class="wrap text-page"><p class="eyebrow accent">Using this website</p><h1>Accessibility.</h1><p>We want people to be able to explore Big 7’s services and contact the company without unnecessary barriers.</p><h2>Navigation and reading</h2><p>The site includes a skip-to-content link, keyboard-operable navigation, visible focus states, descriptive form labels and controls for light and dark themes. Page content remains available without JavaScript.</p><h2>Motion and display</h2><p>The design respects your device’s reduced-motion preference. Text and layouts are designed to adapt to smaller screens and browser zoom. Some features may depend on your browser and assistive technology.</p><h2>Images</h2><p>Illustrative imagery is labelled as AI-generated and is not represented as photography of Big 7’s completed projects.</p><h2>Need help?</h2><p>If something on the site prevents you from accessing information, email <a href="mailto:info@big7construction.com">info@big7construction.com</a>. Include the page and a description of the difficulty. Do not send sensitive information.</p><h2>Preview status</h2><p>This is a design candidate. Its forms do not send inquiries. Testing is documented with the implementation; this statement is not a blanket certification of accessibility compliance.</p></div>'''
    return document('/accessibility','Website Accessibility | Big 7 Construction','Information about keyboard navigation, display preferences, forms and accessibility support for the Big 7 Construction website.',text)


def project():
    text=f'''<div class="wrap text-page"><p class="eyebrow accent">Commercial construction</p><h1>Looking for a commercial crew?</h1><p>Commercial wood framing and drywall are at the core of Big 7’s work. Tell us about your project and the crew support you need.</p><div class="notice-box">Details for the South Fulton project page are being reviewed. We’re not displaying unconfirmed project figures, customer quotes or illustrative imagery as completed work.</div><div class="button-row">{button('Explore Commercial Services','/commercial-industrial','service:enterprise-framing')}{button('Request an Estimate','/commercial-industrial#contact','bid:project','btn-ink')}</div></div>'''
    return document('/south-fulton-distribution','Commercial Project Inquiries | Big 7 Construction','Explore Big 7’s commercial wood framing and drywall services, or tell us about the crew support your project needs.',text,noindex=True)


def notfound():
    text=f'''<div class="wrap text-page"><p class="eyebrow accent">Let’s get you back on track</p><div class="error-number" aria-hidden="true">404</div><h1>That page isn’t here.</h1><p>The link may have changed. You can still find the right service or tell Big 7 about your project.</p><nav class="button-row" aria-label="Page recovery">{button('Commercial Services','/commercial-industrial','bid:recovery-commercial')}{button('Residential Work','/residential-construction','bid:recovery-residential','btn-ink')}{button('Home Repairs','/residential-construction#home-repair','bid:recovery-repairs','btn-ink')}</nav><p style="margin-top:28px"><a href="/">Back to the homepage</a></p></div>'''
    return document('/404','Page Not Found | Big 7 Construction','This page could not be found. Explore Big 7 Construction’s commercial services, residential work and home repairs.',text,noindex=True)


def main():
    SITE.mkdir(exist_ok=True)
    for name,func in {'index.html':home,'commercial-industrial.html':commercial,'residential-construction.html':residential,'accessibility.html':accessibility,'south-fulton-distribution.html':project,'404.html':notfound}.items():
        text=func()
        (SITE/name).write_text(text,encoding='utf-8')
        print(f'Wrote {name}: {len(text.encode()):,} bytes')
    (SITE/'robots.txt').write_text('User-agent: *\nDisallow: /\n')

if __name__=='__main__': main()
