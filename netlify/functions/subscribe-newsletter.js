// Netlify function: lead magnet signup → HubSpot contact + list enrollment
// Accepts JSON body: { email, segment, eventID?, sourceUrl? }
// segment = homeowner | service-provider | real-estate
// eventID is shared with the browser Pixel Lead event for deduplication.

const crypto = require("crypto");

const LIST_IDS = {
  "homeowner":        "18",
  "service-provider": "19",
  "real-estate":      "20",
};

const META_GRAPH_VERSION = "v18.0";

function sha256(s) {
  return crypto.createHash("sha256").update(String(s).trim().toLowerCase()).digest("hex");
}

async function sendCapiLead({ pixelId, accessToken, email, eventID, sourceUrl, clientIp, userAgent, segment }) {
  if (!pixelId || !accessToken) return { skipped: "missing pixel id or access token" };
  const payload = {
    data: [{
      event_name: "Lead",
      event_time: Math.floor(Date.now() / 1000),
      event_id: eventID || undefined,
      event_source_url: sourceUrl || undefined,
      action_source: "website",
      user_data: {
        em: [sha256(email)],
        client_ip_address: clientIp || undefined,
        client_user_agent: userAgent || undefined,
      },
      custom_data: {
        content_name: "Hurricane Checklist 2026",
        content_category: segment || "homeowner",
      },
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

function makeHs(token) {
  return async function hs(method, path, body) {
    const res = await fetch(`https://api.hubapi.com${path}`, {
      method,
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = {};
    try { data = await res.json(); } catch (_) {}
    return { status: res.status, data };
  };
}

exports.handler = async function (event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method not allowed" };
  }

  const token = (process.env.HUBSPOT_API_KEY || "").trim();
  if (!token) {
    return { statusCode: 500, body: JSON.stringify({ error: "HUBSPOT_API_KEY not configured" }) };
  }

  const hs = makeHs(token);

  let email, segment, eventID, sourceUrl;
  try {
    const body = JSON.parse(event.body || "{}");
    email     = (body.email     || "").trim().toLowerCase();
    segment   = (body.segment   || "").trim();
    eventID   = (body.eventID   || "").trim();
    sourceUrl = (body.sourceUrl || "").trim();
  } catch (_) {
    return { statusCode: 400, body: JSON.stringify({ error: "Invalid JSON body" }) };
  }

  if (!email) {
    return { statusCode: 400, body: JSON.stringify({ error: "Missing email" }) };
  }

  // Default unknown segments to homeowner
  const listId = LIST_IDS[segment] || LIST_IDS["homeowner"];

  async function upsertContact(email) {
    let { status, data } = await hs("POST", "/crm/v3/objects/contacts", {
      properties: { email, lifecyclestage: "subscriber" },
    });
    if (status === 201 || status === 200) return data.id;
    if (status === 409) {
      const search = await hs("POST", "/crm/v3/objects/contacts/search", {
        filterGroups: [{ filters: [{ propertyName: "email", operator: "EQ", value: email }] }],
        properties: ["email"],
        limit: 1,
      });
      if (search.data.results && search.data.results.length) return search.data.results[0].id;
      throw new Error("409 but search returned no results");
    }
    const msg = data.message || JSON.stringify(data);
    throw new Error(`HubSpot ${status}: ${msg}`);
  }

  async function addToList(listId, contactId) {
    return hs("PUT", `/crm/v3/lists/${listId}/memberships/add`, [contactId]);
  }

  try {
    const contactId = await upsertContact(email);
    if (!contactId) {
      return { statusCode: 500, body: JSON.stringify({ error: "Failed to create or find contact" }) };
    }
    await addToList(listId, contactId);

    // Fire Meta Conversions API "Lead" event (fail-soft — never break the subscribe response on this).
    try {
      const pixelId     = (process.env.META_PIXEL_ID   || "").trim();
      const accessToken = (process.env.META_CAPI_TOKEN || "").trim();
      const headers     = event.headers || {};
      const clientIp    = (headers["x-nf-client-connection-ip"] || headers["x-forwarded-for"] || "").split(",")[0].trim();
      const userAgent   = headers["user-agent"] || "";
      const capiResult  = await sendCapiLead({
        pixelId, accessToken, email, eventID, sourceUrl, clientIp, userAgent, segment,
      });
      if (capiResult && capiResult.status && capiResult.status >= 400) {
        console.warn("CAPI Lead non-2xx:", capiResult.status, capiResult.data);
      }
    } catch (capiErr) {
      console.warn("CAPI Lead failed (non-fatal):", capiErr && capiErr.message);
    }

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ok: true }),
    };
  } catch (err) {
    console.error("subscribe-newsletter error:", err);
    return { statusCode: 500, body: JSON.stringify({ error: err.message || "Internal error" }) };
  }
};
