// Netlify function: newsletter signup → HubSpot contact creation + list enrollment

const HUBSPOT_TOKEN = process.env.HUBSPOT_API_KEY;

const LIST_IDS = {
  "homeowner":        process.env.HUBSPOT_LIST_HOMEOWNERS        || "18",
  "service-provider": process.env.HUBSPOT_LIST_SERVICE_PROVIDERS  || "19",
  "real-estate":      process.env.HUBSPOT_LIST_RE_PROFESSIONALS   || "20",
};

async function hs(method, path, body) {
  const res = await fetch(`https://api.hubapi.com${path}`, {
    method,
    headers: {
      "Authorization": `Bearer ${HUBSPOT_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (_) {}
  return { status: res.status, data };
}

async function upsertContact(email) {
  // Try to create contact with only standard HubSpot properties
  let { status, data } = await hs("POST", "/crm/v3/objects/contacts", {
    properties: { email, lifecyclestage: "subscriber" },
  });

  if (status === 201 || status === 200) return data.id;

  // 409 = contact already exists — find their ID by email
  if (status === 409) {
    const search = await hs("POST", "/crm/v3/objects/contacts/search", {
      filterGroups: [{ filters: [{ propertyName: "email", operator: "EQ", value: email }] }],
      properties: ["email"],
      limit: 1,
    });
    if (search.data.results && search.data.results.length) {
      return search.data.results[0].id;
    }
  }

  console.error("upsertContact failed:", status, JSON.stringify(data));
  throw new Error(`HubSpot ${status}: ${JSON.stringify(data)}`);
}

async function addToList(listId, contactId) {
  return hs("PUT", `/crm/v3/lists/${listId}/memberships/add`, {
    recordIdsToAdd: [contactId],
  });
}

exports.handler = async function (event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method not allowed" };
  }

  const params = new URLSearchParams(event.body || "");
  const email    = (params.get("email")    || "").trim().toLowerCase();
  const category = (params.get("category") || "").trim();

  if (!email || !category) {
    return { statusCode: 400, body: JSON.stringify({ error: "Missing email or category" }) };
  }

  const listId = LIST_IDS[category];
  if (!listId) {
    return { statusCode: 400, body: JSON.stringify({ error: `Unknown category: ${category}` }) };
  }

  try {
    const contactId = await upsertContact(email);
    if (!contactId) {
      return { statusCode: 500, body: JSON.stringify({ error: "Failed to create or find contact" }) };
    }
    await addToList(listId, contactId);
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ok: true }),
    };
  } catch (err) {
    console.error("Subscribe error:", err);
    return { statusCode: 500, body: JSON.stringify({ error: "Internal error" }) };
  }
};
