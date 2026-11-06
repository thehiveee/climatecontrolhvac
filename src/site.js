/* Climate Control HVAC — site behaviour (no dependencies, ~6 KB)
   - Scroll-reveal animations
   - Cookie consent → loads Google Analytics only after "Accept"
   - Call / lead / exit-offer event tracking
   - Exit-intent discount modal (desktop: cursor leaves toward tabs/close button; mobile: fast scroll-up after reading)
   - Quote form: validation, phone formatting, spam protection (honeypot + time trap + optional Turnstile)
   Config lives in <body data-ga="G-XXXX" data-turnstile="sitekey"> — both are PUBLIC ids, never secrets. */
(function () {
  'use strict';
  var d = document, w = window, body = d.body;
  var GA_ID = body.getAttribute('data-ga') || '';
  var TS_KEY = body.getAttribute('data-turnstile') || '';
  var store = {
    get: function (s, k) { try { return w[s].getItem(k); } catch (e) { return null; } },
    set: function (s, k, v) { try { w[s].setItem(k, v); } catch (e) {} }
  };

  /* ---------- Reveal on scroll ---------- */
  var reveals = d.querySelectorAll('.reveal, .reveal-stagger');
  if ('IntersectionObserver' in w) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    reveals.forEach(function (el) { io.observe(el); });
  } else { reveals.forEach(function (el) { el.classList.add('in'); }); }

  /* ---------- Analytics (consent-gated) ---------- */
  var gaLoaded = false;
  function loadGA() {
    if (gaLoaded || !/^G-[A-Z0-9]+$/.test(GA_ID) || GA_ID === 'G-XXXXXXXXXX') return;
    gaLoaded = true;
    w.dataLayer = w.dataLayer || [];
    w.gtag = function () { w.dataLayer.push(arguments); };
    w.gtag('consent', 'default', { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied', analytics_storage: 'granted' });
    w.gtag('js', new Date());
    w.gtag('config', GA_ID, { anonymize_ip: true });
    var s = d.createElement('script'); s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID; d.head.appendChild(s);
  }
  function track(name, params) { if (gaLoaded && w.gtag) w.gtag('event', name, params || {}); }

  /* ---------- Cookie banner ---------- */
  var cookie = d.getElementById('cookie');
  var consent = store.get('localStorage', 'cc_consent');
  if (consent === 'granted') loadGA();
  else if (!consent && cookie) cookie.hidden = false;
  d.addEventListener('click', function (e) {
    var t = e.target.closest('[data-consent], [data-cookie-settings]');
    if (!t) return;
    if (t.hasAttribute('data-cookie-settings')) { e.preventDefault(); if (cookie) cookie.hidden = false; return; }
    var v = t.getAttribute('data-consent');
    store.set('localStorage', 'cc_consent', v);
    if (cookie) cookie.hidden = true;
    if (v === 'granted') loadGA();
  });

  /* ---------- Click tracking ---------- */
  d.addEventListener('click', function (e) {
    var a = e.target.closest('a[href^="tel:"]');
    if (a) track(a.getAttribute('data-track') || 'call_click', { link_url: a.href, page_path: location.pathname });
  });

  /* ---------- Exit-intent offer ---------- */
  var modal = d.getElementById('exit-offer');
  var lastFocus = null, armed = false;
  setTimeout(function () { armed = true; }, 4000);
  function openOffer(src) {
    if (!modal || !armed || store.get('sessionStorage', 'cc_offer') || location.pathname.indexOf('/thank-you') === 0) return;
    store.set('sessionStorage', 'cc_offer', '1');
    lastFocus = d.activeElement;
    modal.hidden = false;
    var c = modal.querySelector('.offer-close'); if (c) c.focus();
    track('exit_offer_view', { trigger: src });
  }
  function closeOffer() { if (!modal || modal.hidden) return; modal.hidden = true; if (lastFocus && lastFocus.focus) lastFocus.focus(); }
  if (modal) {
    d.addEventListener('mouseout', function (e) { if (!e.relatedTarget && e.clientY <= 0) openOffer('mouse_exit'); });
    var lastY = w.scrollY, lastT = Date.now(), maxDepth = 0;
    w.addEventListener('scroll', function () {
      var y = w.scrollY, t = Date.now();
      maxDepth = Math.max(maxDepth, y / Math.max(1, d.documentElement.scrollHeight - w.innerHeight));
      var v = (lastY - y) / Math.max(1, t - lastT);
      if (w.matchMedia('(pointer:coarse)').matches && maxDepth > 0.4 && v > 2.2 && y > 300) openOffer('fast_scroll_up');
      lastY = y; lastT = t;
    }, { passive: true });
    modal.addEventListener('click', function (e) { if (e.target === modal || e.target.closest('[data-close-offer]')) closeOffer(); });
    d.addEventListener('keydown', function (e) {
      if (modal.hidden) return;
      if (e.key === 'Escape') closeOffer();
      if (e.key === 'Tab') {
        var f = modal.querySelectorAll('a[href], button'); var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && d.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && d.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }

  /* ---------- Quote form ---------- */
  var form = d.querySelector('form[data-lead-form]');
  if (!form) return;
  var started = Date.now();
  var ts = form.querySelector('input[name="ts"]'); if (ts) ts.value = String(started);
  var pg = form.querySelector('input[name="page"]'); if (pg) pg.value = location.pathname;
  var phone = form.elements.phone;
  phone.addEventListener('input', function () {
    var n = phone.value.replace(/\D/g, '').replace(/^1/, '').slice(0, 10);
    var out = n.length > 6 ? '(' + n.slice(0, 3) + ') ' + n.slice(3, 6) + '-' + n.slice(6) : n.length > 3 ? '(' + n.slice(0, 3) + ') ' + n.slice(3) : n;
    phone.value = out;
  });
  form.elements.zip.addEventListener('input', function (e) { e.target.value = e.target.value.replace(/\D/g, '').slice(0, 5); });

  // Turnstile loads only when someone starts the form (keeps first paint fast)
  var tsLoaded = false;
  form.addEventListener('focusin', function () {
    if (tsLoaded || !TS_KEY) return; tsLoaded = true;
    w.onTurnstileLoad = function () { w.turnstile.render('#turnstile', { sitekey: TS_KEY, size: 'flexible', appearance: 'interaction-only' }); };
    var s = d.createElement('script'); s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad&render=explicit'; s.async = true; d.head.appendChild(s);
  });

  var rules = {
    name: function (v) { return v.trim().length >= 2; },
    phone: function (v) { return v.replace(/\D/g, '').replace(/^1(?=\d{10}$)/, '').length === 10; },
    service: function (v) { return !!v; },
    zip: function (v) { return /^\d{5}$/.test(v.trim()); }
  };
  function check(name) {
    var el = form.elements[name], ok = rules[name](el.value);
    el.closest('.field').classList.toggle('invalid', !ok);
    el.setAttribute('aria-invalid', ok ? 'false' : 'true');
    return ok;
  }
  Object.keys(rules).forEach(function (n) {
    form.elements[n].addEventListener('blur', function () { if (form.elements[n].value) check(n); });
    form.elements[n].addEventListener('input', function () { if (form.elements[n].closest('.field').classList.contains('invalid')) check(n); });
  });

  var status = form.querySelector('.form-status');
  function say(msg, ok) { status.textContent = msg; status.className = 'form-status ' + (ok ? 'ok' : 'bad'); }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var bad = Object.keys(rules).filter(function (n) { return !check(n); });
    if (bad.length) { form.elements[bad[0]].focus(); return; }
    if (form.elements.company.value) return;                      // honeypot filled → bot
    if (Date.now() - started < 3000) { say('Please take a moment to check your details, then submit again.', false); return; }
    var btn = form.querySelector('button[type="submit"]'); btn.disabled = true; btn.textContent = 'Sending…';
    var data = {}; new FormData(form).forEach(function (v, k) { data[k] = v; });
    fetch(form.action, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(data) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.j.error || 'Request failed');
        track('generate_lead', { service: data.service });
        location.href = '/thank-you/';
      })
      .catch(function () {
        say('Sorry — that didn’t go through. Please call us at (212) 254-6283 and we’ll help right away.', false);
        btn.disabled = false; btn.textContent = 'Request my free quote';
        if (w.turnstile) try { w.turnstile.reset('#turnstile'); } catch (x) {}
      });
  });
})();
