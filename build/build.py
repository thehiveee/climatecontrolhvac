#!/usr/bin/env python3
"""Build the production site from the design-canvas page files.

Page bodies come from the canvas .dc.html files (single source of truth for page copy);
shared components are rendered from the production partials below (mirrors of the canvas
components, wired to site.js instead of the canvas runtime).
"""
import base64, hashlib, html, json, re, shutil, sys
from datetime import date
from pathlib import Path

CANVAS = Path(sys.argv[1])
STATIC = Path(sys.argv[2])
OUT = Path(sys.argv[3])
SITE = OUT / "site"

CONFIG = {
    "domain": "https://climatecontrolhvac.com",
    "ga_id": "G-XXXXXXXXXX",          # public GA4 Measurement ID — replace before launch
    "turnstile_site_key": "",         # public Cloudflare Turnstile site key (optional; secret lives in env)
    "phone_display": "(212) 254-6283",
    "phone_tel": "+12122546283",
    "discount": "$50",
    "code": "STAY50",
}
TODAY = date(2026, 11, 6).isoformat()

ROUTES = {
    "Main": "/", "Heating": "/heating/", "AirConditioning": "/air-conditioning/",
    "HotWaterHeaters": "/hot-water-heaters/", "CoolingTowers": "/cooling-towers/",
    "Emergency": "/emergency-hvac/", "Privacy": "/privacy-policy/", "Terms": "/terms-and-conditions/",
    "NotFound": "/404.html",
}
BLOBS = {
    "/_blob/8cee1387e9ca424a967f084ccf5abe4f": "/assets/img/logo-480.webp",
    "/_blob/3ca3d4c974d227d0a07db64b19d0eee3": "/assets/img/logo-960.webp",
}

META = {
    "Main": ("Heating & AC Repair NYC | 24/7 HVAC | Climate Control HVAC",
             "Staten Island HVAC company serving NYC, Long Island & NJ. 24/7 heating, AC & hot water repair with a 1-year parts & labor warranty. Call (212) 254-6283."),
    "Heating": ("Heating & Boiler Repair NYC | Climate Control HVAC",
                "24/7 furnace and boiler repair, maintenance and installation in Staten Island, NYC & NJ. Upfront pricing and a 1-year parts & labor warranty."),
    "AirConditioning": ("AC Repair & Installation NYC | Climate Control HVAC",
                        "Rooftop, central, packaged and ductless AC repair, tune-ups and installation across NYC & NJ. 24/7 service, 1-year parts & labor warranty."),
    "HotWaterHeaters": ("Water Heater Repair & Installation NYC | Climate Control HVAC",
                        "Tank, tankless, indirect and heat pump water heaters repaired or replaced 24/7. Bradford White, A. O. Smith, Navien and more. Free estimates."),
    "CoolingTowers": ("Cooling Tower Maintenance & Repair NYC | Climate Control HVAC",
                      "NYC cooling tower inspection, cleaning, disinfection and repair for all brands, with maintenance plans built around city compliance rules."),
    "Emergency": ("24/7 Emergency HVAC Repair NYC | Climate Control HVAC",
                  "No heat, no hot water or no AC? Real people answer 24/7. Emergency HVAC and water heater repair across Staten Island, NYC, Long Island & NJ."),
    "Privacy": ("Privacy Policy | Climate Control HVAC",
                "How Climate Control HVAC collects, uses and protects the information you share through our website, forms and phone calls."),
    "Terms": ("Terms & Conditions | Climate Control HVAC",
              "Terms for estimates, service, our 1-year parts & labor warranty, satisfaction guarantee and website offers from Climate Control HVAC."),
    "NotFound": ("Page Not Found | Climate Control HVAC",
                 "The page you were looking for doesn't exist. Find heating, AC, hot water and 24/7 emergency HVAC service from Climate Control HVAC."),
    "ThankYou": ("Thank You | Climate Control HVAC",
                 "Your estimate request has been received. Climate Control HVAC will be in touch shortly."),
}
NOINDEX = {"NotFound", "ThankYou"}
SERVICE_NAMES = {"Heating": "Heating repair, maintenance and installation",
                 "AirConditioning": "Air conditioning repair, maintenance and installation",
                 "HotWaterHeaters": "Hot water heater repair and installation",
                 "CoolingTowers": "Cooling tower maintenance, compliance and repair",
                 "Emergency": "24/7 emergency HVAC repair"}
CRUMB = {"Heating": "Heating", "AirConditioning": "Air Conditioning", "HotWaterHeaters": "Hot Water Heaters",
         "CoolingTowers": "Cooling Towers", "Emergency": "24/7 Emergency", "Privacy": "Privacy Policy",
         "Terms": "Terms & Conditions"}

PHONE_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"></path></svg>'
FAN_SVG = '<svg class="fan" viewBox="-50 -50 100 100" aria-hidden="true"><g fill="currentColor"><path d="M0-5C9-17 10-36 0-48-10-36-9-17 0-5Z"></path><path d="M0-5C9-17 10-36 0-48-10-36-9-17 0-5Z" transform="rotate(120)"></path><path d="M0-5C9-17 10-36 0-48-10-36-9-17 0-5Z" transform="rotate(240)"></path><circle r="7"></circle></g></svg>'


def call_btn(small, label=None, cls="btn btn-call", track="call_click", extra=""):
    label = label or CONFIG["phone_display"]
    return (f'<a class="{cls}" href="tel:{CONFIG["phone_tel"]}" data-track="{track}"{extra}>'
            f'<span class="ring">{PHONE_SVG}</span><span class="num"><small>{small}</small>{label}</span></a>')


# ---------------- Partials (production mirrors of the canvas components) ----------------
def p_header(active="home", **_):
    items = [("heating", "Heating", "/heating/"), ("ac", "Air Conditioning", "/air-conditioning/"),
             ("water", "Hot Water", "/hot-water-heaters/"), ("tower", "Cooling Towers", "/cooling-towers/"),
             ("emergency", "24/7 Emergency", "/emergency-hvac/")]
    nav = "".join(f'<a href="{u}"{" aria-current=\"page\"" if k == active else ""}>{t}</a>' for k, t, u in items)
    mob = "".join(f'<a href="{u}">{t if k != "water" else "Hot Water Heaters"}</a>' for k, t, u in items)
    return f'''<header class="site-header">
  <div class="topstrip"><div class="wrap">
    <span class="live"><span class="dot" aria-hidden="true"></span><span><strong>Emergency line open 24/7</strong><span class="hide-sm"> · Office 9&nbsp;a.m.–5&nbsp;p.m. daily</span></span></span>
    <span class="hide-sm">780 Richmond Terrace, Staten Island, NY · <a href="mailto:info@climatecontrolny.com" style="color:#fff">info@climatecontrolny.com</a></span>
  </div></div>
  <div class="wrap nav-row" style="position:relative">
    <a class="brand" href="/" aria-label="Climate Control HVAC — home"><img src="/assets/img/logo-480.webp" srcset="/assets/img/logo-360.webp 360w, /assets/img/logo-480.webp 480w, /assets/img/logo-960.webp 960w" sizes="(max-width: 640px) 150px, 180px" alt="Climate Control HVAC logo" width="180" height="64" fetchpriority="high"></a>
    <nav class="nav" aria-label="Main">{nav}</nav>
    {call_btn("Call 24/7", cls="btn btn-call header-cta")}
    <details class="menu">
      <summary aria-label="Open menu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"></path></svg></summary>
      <nav class="menu-panel" aria-label="Mobile"><a href="/">Home</a>{mob}<a class="btn btn-call btn-block" href="tel:{CONFIG["phone_tel"]}" data-track="call_click" style="margin-top:12px;color:#fff">Call {CONFIG["phone_display"]}</a></nav>
    </details>
    <a class="call-icon" href="tel:{CONFIG["phone_tel"]}" aria-label="Call Climate Control HVAC at {CONFIG["phone_display"]}" data-track="call_click">{PHONE_SVG}</a>
  </div>
</header>'''


def p_leadform(service="", **_):
    opts = [("", "Choose one…"), ("heating", "Heating"), ("ac", "Air conditioning"), ("water", "Hot water heater"),
            ("tower", "Cooling tower"), ("emergency", "Emergency repair"), ("other", "Something else")]
    o = "".join(f'<option value="{v}"{" selected" if v == service and v else ""}>{t}</option>' for v, t in opts)
    return f'''<div class="lead-card">
  <div style="display:flex;flex-direction:column;gap:6px"><h2>Get a free estimate</h2><p class="sub">Written quote within 24 hours. No obligation, no hidden costs.</p></div>
  <form class="form" action="/api/lead" method="post" novalidate data-lead-form aria-label="Free estimate request">
    <div class="field"><label for="lf-name">Full name</label><input id="lf-name" name="name" type="text" autocomplete="name" required maxlength="80" placeholder="Jane Smith"><span class="err">Please enter your name.</span></div>
    <div class="field"><label for="lf-phone">Phone</label><input id="lf-phone" name="phone" type="tel" autocomplete="tel" inputmode="tel" required maxlength="20" placeholder="(718) 555-0123"><span class="err">Enter a 10-digit US phone number.</span></div>
    <div class="field"><label for="lf-service">Service needed</label><select id="lf-service" name="service" required>{o}</select><span class="err">Pick a service.</span></div>
    <div class="field"><label for="lf-zip">ZIP code</label><input id="lf-zip" name="zip" type="text" inputmode="numeric" autocomplete="postal-code" maxlength="5" required placeholder="10301"><span class="err">Enter a 5-digit ZIP.</span></div>
    <div class="field full"><label for="lf-msg">What's going on? <span style="font-weight:500;color:#556170">(optional)</span></label><textarea id="lf-msg" name="message" rows="2" maxlength="1000" placeholder="e.g. Boiler won't fire, no heat since this morning"></textarea></div>
    <div class="hp" aria-hidden="true"><label for="lf-company">Company</label><input id="lf-company" name="company" type="text" tabindex="-1" autocomplete="off"></div>
    <input type="hidden" name="ts" value=""><input type="hidden" name="page" value="">
    <div id="turnstile" class="full" style="grid-column:1/-1"></div>
    <button class="btn btn-dark btn-block" type="submit" style="grid-column:1/-1">Request my free quote</button>
    <p class="form-status" role="status" aria-live="polite"></p>
    <p class="form-note">By submitting, you agree to be contacted about your request. We never sell your information. See our <a href="/privacy-policy/">Privacy Policy</a>.</p>
  </form>
  <div class="form-or">or skip the form</div>
  {call_btn("Fastest · 24/7", "Call " + CONFIG["phone_display"], cls="btn btn-call btn-block")}
</div>'''


def p_promise(**_):
    return '''<div class="promise reveal-stagger">
  <div class="item"><span class="seal">Written guarantee</span><div class="big">1<span>&nbsp;yr</span></div><h3>Parts &amp; labor warranty</h3><p>Every part we replace is covered for a full year. The industry norm is 30–60 days.</p></div>
  <div class="item"><span class="seal">Guaranteed</span><div class="big">100<span>%</span></div><h3>Satisfaction, or we make it right</h3><p>If you're not happy with the work, we come back until you are.</p></div>
  <div class="item"><span class="seal">Always on</span><div class="big">24<span>/7</span></div><h3>Emergency service</h3><p>Nights, weekends and holidays. A real person answers and dispatches a technician.</p></div>
  <div class="item"><span class="seal">Full transparency</span><div class="big"><span>$</span>0</div><h3>Hidden costs</h3><p>You approve a clear, written price before any work begins. Free estimates, quoted within 24 hours.</p></div>
</div>'''


def p_ctaband(heading="Don't spend another night without heat.", **_):
    return f'''<section class="cta-band dark" aria-label="Call Climate Control HVAC">
  {FAN_SVG}
  <div class="wrap">
    <div style="display:flex;flex-direction:column;gap:12px"><span class="kicker">Answered 24/7</span><h2>{heading}</h2><p class="lead">One call gets a trained technician on the way — backed by a 1-year parts &amp; labor warranty.</p></div>
    {call_btn("Call now", cls="btn btn-call btn-lg")}
  </div>
</section>'''


def p_footer(**_):
    return f'''<footer class="site-footer">
  <div class="wrap">
    <div class="foot-grid">
      <div class="foot-brand"><img src="/assets/img/logo-480.webp" srcset="/assets/img/logo-360.webp 360w, /assets/img/logo-480.webp 480w" sizes="200px" alt="Climate Control HVAC logo" width="200" height="71" loading="lazy"><p style="color:#36404d">Locally owned and operated on Staten Island. Residential &amp; commercial heating, cooling and hot water for NY and NJ.</p></div>
      <div><h2>Services</h2><ul><li><a href="/heating/">Heating</a></li><li><a href="/air-conditioning/">Air Conditioning</a></li><li><a href="/hot-water-heaters/">Hot Water Heaters</a></li><li><a href="/cooling-towers/">Cooling Towers</a></li><li><a href="/emergency-hvac/">24/7 Emergency Service</a></li></ul></div>
      <div><h2>Contact</h2><ul><li><a href="tel:{CONFIG["phone_tel"]}" data-track="call_click"><strong>{CONFIG["phone_display"]}</strong></a></li><li><a href="mailto:info@climatecontrolny.com">info@climatecontrolny.com</a></li><li><address style="font-style:normal;color:#36404d">780 Richmond Terrace<br>Staten Island, NY</address></li></ul></div>
      <div><h2>Hours</h2><ul style="color:#36404d"><li>Office: 9&nbsp;a.m.–5&nbsp;p.m., Mon–Sun</li><li>Emergency line: 24/7</li></ul></div>
    </div>
    <div class="foot-legal"><span>© {date.today().year if date.today().year >= 2026 else 2026} Climate Control HVAC. All rights reserved.</span>
      <nav aria-label="Legal"><a href="/privacy-policy/">Privacy Policy</a><a href="/terms-and-conditions/">Terms &amp; Conditions</a><a href="#" data-cookie-settings>Cookie settings</a></nav></div>
  </div>
</footer>'''


def p_chrome(**_):
    disc, code = CONFIG["discount"], CONFIG["code"]
    return f'''<div class="sticky-bar" role="region" aria-label="Call now">
  <div class="wrap">
    <p class="msg"><svg class="flame" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.3 1-3.3.3 1.6 1.4 2.8 2.5 2.8z"></path></svg>
      <span><strong>No heat? Don't wait.</strong><span class="long"> Call now for the earliest available technician.</span><small>Real people answer 24/7 · 1-year parts &amp; labor warranty</small></span></p>
    {call_btn("Call now")}
  </div>
</div>
<div class="modal" id="exit-offer" role="dialog" aria-modal="true" aria-labelledby="offer-title" hidden>
  <div class="offer">
    <button class="offer-close" type="button" aria-label="Close offer" data-close-offer><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"></path></svg></button>
    <div class="offer-top">{FAN_SVG.replace('class="fan"', 'class="fan" style="color:#fff"')}
      <p class="kicker" style="justify-content:center;color:#5cc8f5">Wait — before you go</p>
      <p class="offer-amt" id="offer-title">{disc} <span>OFF</span></p>
      <p style="color:#b9c6d4;font-weight:600">your repair or service call</p></div>
    <div class="offer-body">
      <p style="font-size:1.05rem">Call now and mention this code to lock in your discount:</p>
      <span class="code">{code}</span>
      {call_btn("Claim " + disc + " off", cls="btn btn-call btn-lg btn-block", track="offer_call_click")}
      <button class="decline" type="button" data-close-offer>No thanks</button>
      <p class="fine">One per household. Not combinable with other offers. Mention the code when you call or book. <a href="/terms-and-conditions/">Offer terms</a>.</p>
    </div>
  </div>
</div>
<div class="cookie" id="cookie" role="dialog" aria-labelledby="cookie-title" aria-live="polite" hidden>
  <h2 id="cookie-title">Cookies, briefly</h2>
  <p>We use essential cookies to run this site and, with your OK, analytics cookies to see which pages help people most. See our <a href="/privacy-policy/">Privacy Policy</a>.</p>
  <div class="row"><button class="btn btn-dark" type="button" data-consent="granted">Accept analytics</button><button class="btn btn-ghost" type="button" data-consent="denied">Essential only</button></div>
</div>'''


PARTIALS = {"Header": p_header, "LeadForm": p_leadform, "Promise": p_promise,
            "CtaBand": p_ctaband, "Footer": p_footer, "Chrome": p_chrome}


def render_imports(src):
    def rep(m):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        name = attrs.pop("name")
        attrs = {k: html.unescape(v) for k, v in attrs.items() if not k.startswith("hint-") and "{{" not in v}
        return PARTIALS[name](**attrs)
    return re.sub(r'<dc-import\s+([^>]*)></dc-import>', rep, src)


def body_from_canvas(stem):
    raw = (CANVAS / f"{stem}.dc.html").read_text()
    inner = raw.split("<x-dc>", 1)[1].split("</x-dc>", 1)[0]
    inner = re.sub(r"<helmet>.*?</helmet>", "", inner, flags=re.S)
    assert "{{" not in re.sub(r'<dc-import[^>]*></dc-import>', "", inner), f"unresolved hole in {stem}"
    inner = render_imports(inner)
    for b, p in BLOBS.items():
        inner = inner.replace(b, p)
    inner = re.sub(r'href="(\w+)\.dc\.html"', lambda m: f'href="{ROUTES[m.group(1)]}"', inner)
    return inner.strip()


def faq_schema(body):
    qs = re.findall(r"<summary>(.*?)<svg.*?</summary><div class=\"a\">(.*?)</div>", body, flags=re.S)
    if not qs:
        return None
    clean = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ").strip()
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": clean(q), "acceptedAnswer": {"@type": "Answer", "text": clean(a)}} for q, a in qs]}


BUSINESS = {
    "@context": "https://schema.org", "@type": "HVACBusiness", "@id": CONFIG["domain"] + "/#business",
    "name": "Climate Control HVAC", "url": CONFIG["domain"] + "/", "telephone": "+1-212-254-6283",
    "email": "info@climatecontrolny.com", "logo": CONFIG["domain"] + "/assets/img/logo-960.webp",
    "image": CONFIG["domain"] + "/assets/img/og-image.jpg",
    "address": {"@type": "PostalAddress", "streetAddress": "780 Richmond Terrace", "addressLocality": "Staten Island", "addressRegion": "NY", "addressCountry": "US"},
    "areaServed": ["Staten Island", "Manhattan", "Brooklyn", "Queens", "The Bronx", "Long Island", "New Jersey"],
    "openingHoursSpecification": [{"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "opens": "09:00", "closes": "17:00"}],
    "description": "Residential and commercial heating, air conditioning, hot water heater and cooling tower service with 24/7 emergency repair and a 1-year parts & labor warranty.",
}

FONT_CSS = '<style>@font-face{font-family:"Inter";src:url(/assets/fonts/inter-wght.woff2) format("woff2");font-weight:400 800;font-style:normal;font-display:swap}@font-face{font-family:"Archivo";src:url(/assets/fonts/archivo-wdth.woff2) format("woff2");font-weight:700 900;font-stretch:100% 125%;font-style:normal;font-display:swap}@font-face{font-family:"Archivo";src:url(/assets/fonts/archivo-wdth-italic.woff2) format("woff2");font-weight:700 900;font-stretch:100% 125%;font-style:italic;font-display:swap}</style>'
JS_CLASS = "document.documentElement.classList.add('js')"
JS_HASH = "sha256-" + base64.b64encode(hashlib.sha256(JS_CLASS.encode()).digest()).decode()


def page(stem, body, css_v, js_v):
    title, desc = META[stem]
    route = ROUTES.get(stem, "/thank-you/")
    url = CONFIG["domain"] + route
    ld = [BUSINESS]
    if stem in SERVICE_NAMES:
        ld.append({"@context": "https://schema.org", "@type": "Service", "name": SERVICE_NAMES[stem], "serviceType": SERVICE_NAMES[stem],
                   "provider": {"@id": CONFIG["domain"] + "/#business"}, "areaServed": BUSINESS["areaServed"], "url": url})
    if stem in CRUMB:
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": CONFIG["domain"] + "/"},
            {"@type": "ListItem", "position": 2, "name": CRUMB[stem], "item": url}]})
    fq = faq_schema(body)
    if fq:
        ld.append(fq)
    ld_html = "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    robots = '<meta name="robots" content="noindex, follow">' if stem in NOINDEX else '<meta name="robots" content="index, follow, max-image-preview:large">'
    canonical = "" if stem in NOINDEX else f'<link rel="canonical" href="{url}">'
    e = html.escape
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{robots}
{canonical}
<meta name="theme-color" content="#0c1824">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Climate Control HVAC">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{CONFIG["domain"]}/assets/img/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Climate Control HVAC — 24/7 heating, cooling and hot water service in NYC">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{CONFIG["domain"]}/assets/img/og-image.jpg">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/inter-wght.woff2" crossorigin>
<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/archivo-wdth.woff2" crossorigin>
{FONT_CSS}
<link rel="preload" as="image" href="/assets/img/logo-480.webp" type="image/webp">
<link rel="stylesheet" href="/assets/css/site.css?v={css_v}">
<script>{JS_CLASS}</script>
<script defer src="/assets/js/site.js?v={js_v}"></script>
{ld_html}
</head>
<body data-ga="{CONFIG["ga_id"]}" data-turnstile="{CONFIG["turnstile_site_key"]}">
{body}
</body>
</html>
'''


THANKYOU = '''<div class="page">
<a class="skip" href="#main">Skip to content</a>
<dc-import name="Header" active="none"></dc-import>
<main id="main">
<section class="section nf" aria-labelledby="ty-title">
  <div class="wrap" style="display:flex;flex-direction:column;align-items:center;gap:20px">
    <span class="seal anim-up">Request received</span>
    <h1 id="ty-title" class="anim-up d1">Thanks — we're on it.</h1>
    <p class="lead anim-up d2" style="max-width:560px">We'll call you back shortly with next steps, and your written quote follows within 24 hours. If it's urgent, don't wait for us — call now.</p>
    <div class="anim-up d3">CALLBTN</div>
    <a class="textlink anim-up d4" href="/">Back to home</a>
  </div>
</section>
</main>
<dc-import name="Footer"></dc-import>
</div>'''


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, SITE)
    # drop full-res brand originals from the deploy (kept in /brand)
    (OUT / "brand").mkdir()
    for f in ["logo-1451.png", "logo-1451.webp", "logo-480.png", "logo-960.png", "emblem.png", "emblem-512.webp"]:
        p = SITE / "assets/img" / f
        if p.exists():
            shutil.move(str(p), OUT / "brand" / f)
    # keep readable sources alongside, ship minified
    import subprocess
    (OUT / "src").mkdir()
    for rel in ["assets/css/site.css", "assets/js/site.js"]:
        shutil.copy(SITE / rel, OUT / "src" / Path(rel).name)
        subprocess.run([str(Path(__file__).parent / "node_modules/.bin/esbuild"), str(SITE / rel), "--minify", "--outfile=" + str(SITE / rel), "--allow-overwrite", "--log-level=warning"], check=True)
    css_v = hashlib.md5((SITE / "assets/css/site.css").read_bytes()).hexdigest()[:10]
    js_v = hashlib.md5((SITE / "assets/js/site.js").read_bytes()).hexdigest()[:10]
    for stem, route in ROUTES.items():
        body = body_from_canvas(stem)
        target = SITE / ("404.html" if stem == "NotFound" else route.strip("/") + "/index.html" if route != "/" else "index.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(stem, body, css_v, js_v))
    ty = render_imports(THANKYOU).replace("CALLBTN", call_btn("Urgent? Call 24/7", cls="btn btn-call btn-lg"))
    (SITE / "thank-you").mkdir(exist_ok=True)
    (SITE / "thank-you/index.html").write_text(page("ThankYou", ty, css_v, js_v))

    # sitemap + robots
    pri = {"/": "1.0", "/emergency-hvac/": "0.9", "/privacy-policy/": "0.3", "/terms-and-conditions/": "0.3"}
    urls = "".join(f"  <url><loc>{CONFIG['domain']}{r}</loc><lastmod>{TODAY}</lastmod><priority>{pri.get(r, '0.8')}</priority></url>\n"
                   for s, r in ROUTES.items() if s not in NOINDEX)
    (SITE / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /thank-you/\nDisallow: /api/\n\nSitemap: {CONFIG['domain']}/sitemap.xml\n")
    (SITE / "site.webmanifest").write_text(json.dumps({
        "name": "Climate Control HVAC", "short_name": "Climate Control", "start_url": "/", "display": "browser",
        "background_color": "#ffffff", "theme_color": "#0c1824",
        "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, indent=2))
    shutil.copytree(Path(__file__).parent / "project-files", OUT, dirs_exist_ok=True)
    toml = (OUT / "netlify.toml").read_text()
    assert JS_HASH in toml, "CSP hash in netlify.toml is stale: " + JS_HASH
    # compress PNG icons (lossless re-encode + palette where it is visually identical)
    from PIL import Image
    for png in SITE.glob("*.png"):
        im = Image.open(png)
        q = im.convert("RGBA").quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        q.save(png, optimize=True)
    print("built", sorted(str(p.relative_to(SITE)) for p in SITE.rglob("*.html")), JS_HASH)


if __name__ == "__main__":
    main()
