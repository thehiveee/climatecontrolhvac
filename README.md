# Climate Control HVAC — website

Static, dependency-free site (HTML + 1 CSS + 1 JS file), built for Netlify, with an Apache `.htaccess` fallback.
10 pages · ~720 KB total including fonts and images · Lighthouse (mobile): Performance 99, Accessibility 100, Best Practices 100, SEO 100.

```
site/                    ← the deployable website (publish directory)
netlify/functions/lead.mjs  ← quote-form handler (server-side; holds no secrets in code)
netlify.toml             ← HTTPS/HSTS, security headers + CSP, caching, 301 redirects from old URLs
.env.example             ← the environment variables to set in Netlify (never commit real values)
src/                     ← readable (un-minified) site.css and site.js
brand/                   ← high-res transparent logo (1451 px PNG/WebP) + emblem
```

## Deploying on Vercel
`vercel.json` tells Vercel to serve the `site/` folder (no build step), and `api/lead.mjs` runs the quote form handler at `/api/lead`. HTTPS is automatic. Headers, CSP and 301 redirects mirror `netlify.toml`.
In Vercel → Project → Settings, keep **Root Directory** empty and **Framework Preset** as "Other". Add the environment variables from `.env.example` under **Environment Variables**, then redeploy.

## Launch in 5 steps (Netlify shown; Vercel works the same — see above)
1. **Deploy**: push this folder to a Git repo → "Add new site" in Netlify → it reads `netlify.toml` automatically. Point `climatecontrolhvac.com` DNS at Netlify; HTTPS certificate is issued automatically.
2. **Lead emails**: create a free [Resend](https://resend.com) account, verify the domain, then set `RESEND_API_KEY`, `LEAD_TO_EMAIL`, `LEAD_FROM_EMAIL` in Netlify → Site settings → Environment variables.
3. **Analytics**: create a GA4 property and replace `G-XXXXXXXXXX` in every page's `<body data-ga="…">` (search & replace). It's a public ID, not a secret. GA loads **only after** the visitor clicks "Accept analytics". Events tracked: `call_click`, `offer_call_click`, `exit_offer_view`, `generate_lead`. Mark `call_click` and `generate_lead` as key events.
4. **(Optional) Turnstile bot check**: create a Cloudflare Turnstile widget → put the *site key* in `<body data-turnstile="…">` and the *secret key* in `TURNSTILE_SECRET_KEY`.
5. **Search Console**: verify the domain and submit `https://climatecontrolhvac.com/sitemap.xml`. Update the Google Business Profile website link.

## Launch checklist — where each item lives
| Item | How it's handled |
|---|---|
| Privacy policy page | `/privacy-policy/` (covers forms, analytics, cookies, Turnstile, NY data security) |
| Terms & conditions page | `/terms-and-conditions/` (estimates, 1-yr warranty terms, guarantee, offer terms) |
| Secrets off the frontend | API keys only in env vars, read by `netlify/functions/lead.mjs`; `.env` git-ignored; front end holds only public IDs |
| Force HTTPS | Netlify auto-redirects + HSTS header (`netlify.toml`); `.htaccess` rewrite for Apache |
| Cookie consent banner | Accept / Essential-only, remembered; "Cookie settings" link in footer reopens it; GA blocked until accepted |
| Meta titles + descriptions | Unique per page, plus canonical URLs and JSON-LD (HVACBusiness, Service, Breadcrumb, FAQPage) |
| Social preview image | `/assets/img/og-image.jpg` (1200×630) + Open Graph + Twitter card tags |
| Favicon | `favicon.ico`, 32 px PNG, Apple touch icon, 192/512 icons, `site.webmanifest` |
| Sitemap + robots.txt | `/sitemap.xml`, `/robots.txt` (thank-you page and API excluded) |
| Alt text on images | All images have descriptive alt; decorative SVGs are `aria-hidden` |
| Compress images | WebP logos with `srcset`, quantized PNG icons, progressive JPEG OG; fonts self-hosted and subset (~105 KB total) |
| Check page load speed | Lighthouse mobile: Perf 99, LCP ≈ 2.0–2.2 s, CLS 0, TBT ≤ 60 ms |
| Fix colour contrast | Brand colours deepened for text to pass WCAG AA; axe-core: 0 violations on all pages, desktop + mobile |
| Mobile friendly | Mobile-first layout, 44 px+ tap targets, no horizontal scroll at 390 px, sticky call bar |
| Custom 404 page | `/404.html` (wired in Netlify automatically and in `.htaccess`) |
| Fix broken links | Link crawl: 0 broken. Old WordPress URLs 301-redirect to the new pages |
| Form validation | Client-side (inline errors, phone auto-format, ZIP sanitising) **and** server-side |
| Spam protection | Honeypot, 3-second time trap, server validation, link-spam filter, per-IP rate limit, optional Turnstile |
| Set up analytics | GA4 with Consent Mode, call/lead/offer events (add your ID — step 3) |
| One clear call to action | **Call (212) 254-6283** is the primary action everywhere (red, animated); the quote form is secondary |

## Before go-live, confirm with the client
- **Exit-offer discount**: `$50 OFF`, code `STAY50` is a suggested placeholder. Confirm the amount, code and conditions (edit in each page's exit modal, plus Terms §5).
- **Hours wording**: their old site says "9 a.m.–5 p.m." *and* "24/7 emergency". The new site presents this as "Office 9–5 daily · Emergency line 24/7". Confirm that's accurate.
- **Terms placeholders**: `[30]` days for the satisfaction guarantee, and `[Accepted payment methods]`. Have the privacy policy and terms reviewed by their attorney.
- **Reviews**: four real testimonials from their current site (one obvious typo corrected: "prompted" → "prompt"). Ask for permission to add star ratings or Google reviews if wanted.
- **Photos**: none were usable from the old site. Real photos of Ali, the team and the vans would raise trust further.
