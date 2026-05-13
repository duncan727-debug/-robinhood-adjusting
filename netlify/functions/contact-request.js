// Contact form / Free Claim Review handler.
// Accepts JSON body: { first_name, last_name, email, phone, role, message, sourceUrl }
// Upserts a HubSpot contact (lifecyclestage=lead, hs_lead_status=NEW) and fires a Meta CAPI "Lead" event.
// Email notification to Duncan is handled by Netlify Forms (configured at the site level).

const crypto = require("crypto");

const META_GRAPH_VERSION = "v18.0";

function sha256(s) {
  return crypto.createHash("sha256").update(String(s).trim().toLowerCase()).digest("hex");
}

function digits(s) {
  return String(s || "").replace(/\D/g, "");
}

function makeHs(token) {
  return async function hs(method, path, body) {
    const res = await fetch(`https://api.hubapi.com${path}`, {
      method,
      headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = {};
    try { data = await res.json(); } catch (_) {}
    return { status: res.status, data };
  };
}

async function sendCapiLead({ pixelId, accessToken, email, phone, sourceUrl, clientIp, userAgent }) {
  if (!pixelId || !accessToken) return { skipped: "missing pixel id or access token" };
  const userData = {
    em: [sha256(email)],
    client_ip_address: clientIp || undefined,
    client_user_agent: userAgent || undefined,
  };
  if (phone) userData.ph = [sha256(digits(phone))];
  const payload = {
    data: [{
      event_name: "Lead",
      event_time: Math.floor(Date.now() / 1000),
      event_source_url: sourceUrl || undefined,
      action_source: "website",
      user_data: userData,
      custom_data: { content_name: "Free Claim Review Request", content_category: "claim-review" },
    }],
  };
  const url = `https://graph.facebook.com/${META_GRAPH_VERSION}/${pixelId}/events?access_token=${encodeURIComponent(accessToken)}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  let data = {};
  try { data = await res.json(); } catch (_) {}
  return { status: res.status, data };
}

exports.handler = async function (event) {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "Method not allowed" };

  let body = {};
  try { body = JSON.parse(event.body || "{}"); }
  catch (_) { return { statusCode: 400, body: JSON.stringify({ error: "Invalid JSON body" }) }; }

  const first_name = (body.first_name || "").trim();
  const last_name  = (body.last_name  || "").trim();
  const email      = (body.email      || "").trim().toLowerCase();
  const phone      = (body.phone      || "").trim();
  const role       = (body.role       || "").trim();
  const message    = (body.message    || "").trim();
  const sourceUrl  = (body.sourceUrl  || "").trim();

  if (!email) return { statusCode: 400, body: JSON.stringify({ error: "Missing email" }) };

  const headers   = event.headers || {};
  const clientIp  = (headers["x-nf-client-connection-ip"] || headers["x-forwarded-for"] || "").split(",")[0].trim();
  const userAgent = headers["user-agent"] || "";

  const result = { hubspot: null, capi: null };

  const token = (process.env.HUBSPOT_API_KEY || "").trim();
  if (token) {
    const hs = makeHs(token);
    try {
      const props = {
        email, firstname: first_name, lastname: last_name, phone,
        lifecyclestage: "lead",
        hs_lead_status: "NEW",
        message,
        hs_analytics_source: "OFFLINE",
        hs_analytics_source_data_1: "claim-review-form",
      };
      Object.keys(props).forEach((k) => { if (!props[k]) delete props[k]; });

      let { status, data } = await hs("POST", "/crm/v3/objects/contacts", { properties: props });
      let contactId = null;
      if (status === 201 || status === 200) {
        contactId = data.id;
      } else if (status === 409) {
        const search = await hs("POST", "/crm/v3/objects/contacts/search", {
          filterGroups: [{ filters: [{ propertyName: "email", operator: "EQ", value: email }] }],
          properties: ["email"], limit: 1,
        });
        if (search.data.results && search.data.results.length) {
          contactId = search.data.results[0].id;
          await hs("PATCH", `/crm/v3/objects/contacts/${contactId}`, { properties: props });
        }
      }
      result.hubspot = { contactId, status };
    } catch (err) {
      result.hubspot = { error: err.message };
    }
  } else {
    result.hubspot = { skipped: "HUBSPOT_API_KEY not configured" };
  }

  try {
    result.capi = await sendCapiLead({
      pixelId:     (process.env.META_PIXEL_ID   || "").trim(),
      accessToken: (process.env.META_CAPI_TOKEN || "").trim(),
      email, phone, sourceUrl, clientIp, userAgent,
    });
  } catch (err) {
    result.capi = { error: err.message };
  }

  return {
    statusCode: 200,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ok: true, result }),
  };
};
