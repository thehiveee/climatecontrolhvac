// Vercel entry point for the quote form (POST /api/lead).
// Reuses the same handler as Netlify so validation and spam rules live in one place.
// Set RESEND_API_KEY, LEAD_TO_EMAIL, LEAD_FROM_EMAIL (and optionally TURNSTILE_SECRET_KEY)
// in Vercel → Project → Settings → Environment Variables.
import handler from '../netlify/functions/lead.mjs';

export default {
  fetch(request) {
    const ip = (request.headers.get('x-forwarded-for') || '').split(',')[0].trim() || request.headers.get('x-real-ip') || 'unknown';
    return handler(request, { ip });
  }
};
