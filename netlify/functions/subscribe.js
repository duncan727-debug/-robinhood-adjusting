// Netlify function: newsletter signup → HubSpot contact creation + list enrollment (v2)

const LIST_IDS = {
  "homeowner":        "18",
  "service-provider": "19",
  "real-estate":      "20",
};

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
      throw new Error(`409 but search returned no results`);
    }
    const msg = data.message || JSON.stringify(data);
    throw new Error(`HubSpot ${status}: ${msg}`);
  }

  async function addToList(listId, contactId) {
    return hs("PUT", `/crm/v3/lists/${listId}/memberships/add`, [contactId]);
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
    return { statusCode: 500, body: JSON.stringify({ error: err.message || "Internal error" }) };
  }
};
