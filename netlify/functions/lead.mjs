// Quote-form handler (Netlify Function). All secrets come from environment variables —
// nothing sensitive ever ships to the browser.
//
//   RESEND_API_KEY        API key for https://resend.com (email delivery)
//   LEAD_TO_EMAIL         where new leads are sent, e.g. info@climatecontrolny.com
//   LEAD_FROM_EMAIL       verified sender, e.g. "Website <leads@climatecontrolhvac.com>"
//   TURNSTILE_SECRET_KEY  (optional) Cloudflare Turnstile secret — enables bot verification
//
// Spam protection, in layers: honeypot field, minimum fill time, server-side validation,
// optional Turnstile verification, and a per-IP rate limit.

const SERVICES = { heating: 'Heating', ac: 'Air conditioning', water: 'Hot water heater', tower: 'Cooling tower', emergency: 'Emergency repair', other: 'Something else' };
const hits = new Map(); // best-effort per-instance rate limit

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function respond(req, status, body) {
  const wantsJson = (req.headers.get('accept') || '').includes('application/json');
  if (wantsJson) return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
  if (status < 300) return new Response(null, { status: 303, headers: { location: '/thank-you/' } });
  return new Response(`<p>${esc(body.error || 'Something went wrong')}. Please call (212) 254-6283.</p><p><a href="javascript:history.back()">Go back</a></p>`, { status, headers: { 'content-type': 'text/html; charset=utf-8' } });
}

export default async (req, context) => {
  if (req.method !== 'POST') return new Response('Method not allowed', { status: 405, headers: { allow: 'POST' } });

  const ip = context?.ip || req.headers.get('x-nf-client-connection-ip') || 'unknown';
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((t) => now - t < 10 * 60 * 1000);
  if (recent.length >= 5) return respond(req, 429, { error: 'Too many requests' });
  hits.set(ip, [...recent, now]);

  let data = {};
  const type = req.headers.get('content-type') || '';
  try {
    if (type.includes('application/json')) data = await req.json();
    else data = Object.fromEntries((await req.formData()).entries());
  } catch { return respond(req, 400, { error: 'Invalid request' }); }

  // 1) Honeypot — real people never see this field. Pretend success so bots don't adapt.
  if (data.company) return respond(req, 200, { ok: true });
  // 2) Time trap — forms submitted within 3s of page load are bots.
  const ts = Number(data.ts);
  if (ts && now - ts < 3000) return respond(req, 200, { ok: true });

  // 3) Server-side validation (never trust the browser)
  const name = String(data.name || '').trim().slice(0, 80);
  const phone = String(data.phone || '').replace(/\D/g, '').replace(/^1(?=\d{10}$)/, '');
  const service = String(data.service || '');
  const zip = String(data.zip || '').trim();
  const message = String(data.message || '').trim().slice(0, 1000);
  if (name.length < 2 || phone.length !== 10 || !SERVICES[service] || !/^\d{5}$/.test(zip)) {
    return respond(req, 422, { error: 'Please check your details' });
  }
  if ((message.match(/https?:\/\//g) || []).length > 2) return respond(req, 200, { ok: true }); // link spam

  // 4) Optional Cloudflare Turnstile
  if (process.env.TURNSTILE_SECRET_KEY) {
    const token = data['cf-turnstile-response'];
    if (!token) return respond(req, 400, { error: 'Bot check missing' });
    const v = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST', body: new URLSearchParams({ secret: process.env.TURNSTILE_SECRET_KEY, response: token, remoteip: ip })
    }).then((r) => r.json()).catch(() => ({ success: false }));
    if (!v.success) return respond(req, 400, { error: 'Bot check failed' });
  }

  // 5) Deliver the lead
  const { RESEND_API_KEY, LEAD_TO_EMAIL, LEAD_FROM_EMAIL } = process.env;
  if (!RESEND_API_KEY || !LEAD_TO_EMAIL || !LEAD_FROM_EMAIL) {
    console.error('Lead email not configured — set RESEND_API_KEY, LEAD_TO_EMAIL, LEAD_FROM_EMAIL');
    return respond(req, 500, { error: 'Form temporarily unavailable' });
  }
  const pretty = `(${phone.slice(0, 3)}) ${phone.slice(3, 6)}-${phone.slice(6)}`;
  const urgent = service === 'emergency';
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${RESEND_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: LEAD_FROM_EMAIL, to: [LEAD_TO_EMAIL],
      subject: `${urgent ? '🚨 EMERGENCY ' : ''}New estimate request — ${SERVICES[service]} — ${zip}`,
      html: `<h2>New website lead</h2><table cellpadding="6">
        <tr><td><b>Name</b></td><td>${esc(name)}</td></tr>
        <tr><td><b>Phone</b></td><td><a href="tel:+1${phone}">${pretty}</a></td></tr>
        <tr><td><b>Service</b></td><td>${esc(SERVICES[service])}</td></tr>
        <tr><td><b>ZIP</b></td><td>${esc(zip)}</td></tr>
        <tr><td><b>Message</b></td><td>${esc(message) || '—'}</td></tr>
        <tr><td><b>Page</b></td><td>${esc(data.page)}</td></tr></table>
        <p>Promise: written quote within 24 hours.</p>`
    })
  });
  if (!r.ok) { console.error('Resend error', r.status, await r.text()); return respond(req, 502, { error: 'Could not send' }); }
  return respond(req, 200, { ok: true });
};

export const config = { path: '/api/lead' };
