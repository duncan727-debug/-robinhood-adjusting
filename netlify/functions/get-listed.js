// Netlify function: "Get Listed" form → HubSpot company + contact + review task

const SITE_URL = "https://robinhoodadjusting.com";

const TRADE_TO_INDUSTRY = {
  "Roofing":              "CONSTRUCTION",
  "Restoration":          "CONSTRUCTION",
  "HVAC":                 "CONSTRUCTION",
  "Plumbing":             "CONSTRUCTION",
  "General Contractor":   "CONSTRUCTION",
  "Property Management":  "REAL_ESTATE",
  "Real Estate":          "REAL_ESTATE",
  "Other":                "CONSTRUCTION",
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

function successPage(businessName) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Request Received — Robinhood Adjusting</title>
<style>
  body { margin:0; padding:0; background:#f5f5f5; font-family:Georgia,serif; }
  .wrap { max-width:560px; margin:60px auto; background:#fff; border-top:5px solid #c9922a; padding:48px 40px; text-align:center; }
  h1 { color:#0f2d4a; font-size:26px; margin:0 0 16px; }
  p { color:#444; font-size:16px; line-height:1.7; margin:0 0 20px; }
  .highlight { background:#f8f4ee; border-left:4px solid #c41e3a; padding:14px 18px; text-align:left; margin:24px 0; font-size:15px; color:#222; }
  a.btn { display:inline-block; background:#c41e3a; color:#fff; padding:12px 28px; text-decoration:none; border-radius:4px; font-family:Arial,sans-serif; font-size:14px; font-weight:bold; }
  .footer { color:#999; font-size:12px; margin-top:32px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Request received — thank you.</h1>
  <div class="highlight"><strong>${businessName}</strong> has been submitted for review.</div>
  <p>We review every listing request personally. If your business is a good fit for our directory, we'll add you and send a confirmation.</p>
  <p>Most reviews are completed within 1–2 business days.</p>
  <a href="${SITE_URL}/providers/index.html" class="btn">View the Directory</a>
  <p class="footer">Duncan Littlejohn · Public Adjuster · Wellington, FL · 561-772-7528</p>
</div>
</body>
</html>`;
}

function errorPage(message) {
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Robinhood Adjusting</title></head>
<body style="font-family:Arial,sans-serif;text-align:center;padding:60px 20px;color:#444;">
<h2>Something went wrong</h2><p>${message}</p>
<p><a href="${SITE_URL}/providers/index.html" style="color:#c41e3a;">Return to Provider Directory</a></p>
</body>
</html>`;
}

exports.handler = async function (event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method not allowed" };
  }

  const token = (process.env.HUBSPOT_API_KEY || "").trim();
  if (!token) {
    return { statusCode: 500, headers: { "Content-Type": "text/html" },
      body: errorPage("Configuration error. Please email us directly.") };
  }

  const hs = makeHs(token);

  const params = new URLSearchParams(event.body || "");
  const businessName = (params.get("business_name") || "").trim();
  const contactName  = (params.get("contact_name")  || "").trim();
  const email        = (params.get("email")          || "").trim().toLowerCase();
  const phone        = (params.get("phone")          || "").trim();
  const trade        = (params.get("trade")          || "Other").trim();
  const city         = (params.get("city")           || "").trim();
  const website      = (params.get("website")        || "").trim();

  if (!businessName || !email) {
    return { statusCode: 400, headers: { "Content-Type": "text/html" },
      body: errorPage("Please fill in your business name and email.") };
  }

  const industry = TRADE_TO_INDUSTRY[trade] || "CONSTRUCTION";
  const companyProps = {
    name: businessName,
    city: city || "Palm Beach County",
    state: "Florida",
    country: "United States",
    industry,
    description: trade,
    phone: phone || undefined,
  };
  if (website) {
    companyProps.domain = website.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }

  // Create company
  let companyId = null;
  const { status: cs, data: cd } = await hs("POST", "/crm/v3/objects/companies",
    { properties: companyProps });
  if (cs === 201 || cs === 200) {
    companyId = cd.id;
  } else if (cs === 409) {
    const search = await hs("POST", "/crm/v3/objects/companies/search", {
      filterGroups: [{ filters: [{ propertyName: "name", operator: "EQ", value: businessName }] }],
      properties: ["name"], limit: 1,
    });
    companyId = search.data.results?.[0]?.id || null;
  }

  // Create contact
  const nameParts = contactName.split(/\s+/);
  const firstName = nameParts[0] || contactName;
  const lastName  = nameParts.slice(1).join(" ") || "";
  let contactId = null;
  const contactProps = {
    email,
    firstname: firstName,
    lastname: lastName,
    phone: phone || undefined,
    city: city || undefined,
    state: "Florida",
    newsletter_category: "service-provider",
    hs_lead_status: "NEW",
  };
  const { status: cts, data: ctd } = await hs("POST", "/crm/v3/objects/contacts",
    { properties: contactProps });
  if (cts === 201 || cts === 200) {
    contactId = ctd.id;
  } else if (cts === 409) {
    const search = await hs("POST", "/crm/v3/objects/contacts/search", {
      filterGroups: [{ filters: [{ propertyName: "email", operator: "EQ", value: email }] }],
      properties: ["email"], limit: 1,
    });
    contactId = search.data.results?.[0]?.id || null;
  }

  // Associate contact ↔ company
  if (contactId && companyId) {
    await hs("PUT",
      `/crm/v3/objects/contacts/${contactId}/associations/companies/${companyId}/contact_to_company`,
      null);
  }

  // Create review task for Duncan
  const dueTs = Date.now() + 86400000; // due tomorrow
  const taskProps = {
    hs_task_subject: `Listing request: ${businessName} [${trade}]`,
    hs_task_body: [
      `Business: ${businessName}`,
      `Contact: ${contactName} <${email}>`,
      `Trade: ${trade}`,
      `City: ${city || "not specified"}`,
      `Phone: ${phone || "not provided"}`,
      `Website: ${website || "not provided"}`,
      "",
      "Action: Review listing quality, verify details, add to directory if approved.",
    ].join("\n"),
    hs_task_status: "NOT_STARTED",
    hs_task_type: "TODO",
    hs_timestamp: dueTs,
  };
  const { data: td } = await hs("POST", "/crm/v3/objects/tasks", { properties: taskProps });
  const taskId = td?.id;
  if (taskId && contactId) {
    await hs("PUT",
      `/crm/v3/objects/tasks/${taskId}/associations/contacts/${contactId}/task_to_contact`,
      null);
  }

  return {
    statusCode: 200,
    headers: { "Content-Type": "text/html" },
    body: successPage(businessName),
  };
};
