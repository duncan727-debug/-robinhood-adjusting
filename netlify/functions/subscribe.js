// Netlify function: handles newsletter signup form → HubSpot contact creation + list enrollment
// Triggered by form POST to /.netlify/functions/subscribe

const HUBSPOT_API_KEY = process.env.HUBSPOT_API_KEY;

const LIST_IDS = {
  homeowner:        process.env.HUBSPOT_LIST_HOMEOWNERS       || "18",
  "service-provider": process.env.HUBSPOT_LIST_SERVICE_PROVIDERS || "19",
  "real-estate":    process.env.HUBSPOT_LIST_RE_PROFESSIONALS  || "20",
};

async function hubspot(method, path, body) {
  const res = await fetch(`https://api.hubapi.com${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${HUBSPOT_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, data: await res.json().catch(() => ({})) };
}

async function upsertContact(email, category) {
  // Try to create; if 409 conflict the contact already exists — fetch their ID
  let { status, data } = await hubspot("POST", "/crm/v3/objects/contacts", {
    properties: {
      email,
      hs_lead_status: "NEW",
      lifecyclestage: "subscriber",
      newsletter_category: category,
    },
  });

  if (status === 409) {
    // Existing contact — get ID by email, then write category so drip.py can read it
    const search = await hubspot("POST", "/crm/v3/objects/contacts/search", {
      filterGroups: [{ filters: [{ propertyName: "email", operator: "EQ", value: email }] }],
      properties: ["email"],
      limit: 1,
    });
    if (search.data.results?.length) {
      const id = search.data.results[0].id;
      await hubspot("PATCH", `/crm/v3/objects/contacts/${id}`, {
        properties: { newsletter_category: category },
      });
      return id;
    }
    return null;
  }

  if (status === 200 || status === 201) return data.id;
  return null;
}

async function addToList(listId, contactId) {
  return hubspot("PUT", `/crm/v3/lists/${listId}/memberships/add`, {
    recordIdsToAdd: [contactId],
  });
}

export async function handler(event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method not allowed" };
  }

  if (!HUBSPOT_API_KEY) {
    console.error("HUBSPOT_API_KEY not set");
    return { statusCode: 500, body: "Server configuration error" };
  }

  // Parse form body (URL-encoded from Netlify Forms or direct fetch)
  const params = new URLSearchParams(event.body);
  const email    = params.get("email")?.trim().toLowerCase();
  const category = params.get("category")?.trim();

  if (!email || !category) {
    return { statusCode: 400, body: JSON.stringify({ error: "Missing email or category" }) };
  }

  const listId = LIST_IDS[category];
  if (!listId) {
    return { statusCode: 400, body: JSON.stringify({ error: `Unknown category: ${category}` }) };
  }

  try {
    const contactId = await upsertContact(email, category);
    if (!contactId) {
      return { statusCode: 500, body: JSON.stringify({ error: "Failed to create contact" }) };
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
}
