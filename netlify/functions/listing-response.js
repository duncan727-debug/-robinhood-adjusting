/**
 * Netlify function: handles yes/no responses to listing outreach emails.
 *
 * GET /.netlify/functions/listing-response?company_id=X&contact_id=Y&action=yes|no
 *
 * YES flow:
 *   1. Update HubSpot contact hs_lead_status → CONNECTED
 *   2. Enroll contact in Newsletter - Service Providers list (list ID 6)
 *   3. Update HubSpot company listing_status → confirmed
 *   4. Update crm/directory_companies.json in GitHub: verified=true
 *   5. Patch site/providers/index.html badge for this company
 *   → Returns "You're listed" success page
 *
 * NO flow:
 *   1. Update HubSpot contact hs_lead_status → UNQUALIFIED
 *   → Returns "Thanks for letting us know" page
 *
 * Required Netlify env vars:
 *   HUBSPOT_API_KEY
 *   GITHUB_TOKEN       (repo scope — to commit JSON + HTML updates)
 *   GITHUB_OWNER       (duncan727-debug)
 *   GITHUB_REPO        (-robinhood-adjusting)
 */

const SITE_URL    = "https://robinhoodadjusting.com";
const GITHUB_REF  = "main";
const GITHUB_API_VERSION = "2022-11-28";

// ── helpers ──────────────────────────────────────────────────────────────────

async function moveDealStage(companyId, stageId, token) {
  if (!companyId) return;
  const assoc = await hs("GET",
    `/crm/v3/objects/companies/${companyId}/associations/deals`, undefined, token);
  const dealIds = (assoc.data?.results || []).map(r => r.id);
  for (const dealId of dealIds) {
    await hs("PATCH", `/crm/v3/objects/deals/${dealId}`,
      { properties: { dealstage: stageId } }, token);
  }
}

async function hs(method, path, body, token) {
  const res = await fetch(`https://api.hubapi.com${path}`, {
    method,
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type":  "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (_) {}
  return { status: res.status, data };
}

function githubHeaders(ghToken) {
  return {
    Authorization: `Bearer ${ghToken}`,
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
    "User-Agent": "robinhood-adjusting-netlify",
    "X-GitHub-Api-Version": GITHUB_API_VERSION,
  };
}

async function ghRequest(url, options = {}) {
  const res = await fetch(
    url,
    {
      ...options,
      headers: { ...options.headers },
    }
  );

  let data = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch (_) { data = { raw: text }; }
  }

  if (!res.ok) {
    const message = data?.message || res.statusText || "GitHub API request failed";
    throw new Error(`GitHub ${res.status} ${message}`);
  }

  return data || {};
}

async function ghGet(path, ghToken, owner, repo, ref = GITHUB_REF) {
  return ghRequest(
    `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path).replace(/%2F/g, "/")}?ref=${encodeURIComponent(ref)}`,
    { headers: githubHeaders(ghToken) }
  );
}

async function ghPut(path, content, sha, message, ghToken, owner, repo, ref = GITHUB_REF) {
  if (!sha) throw new Error(`Missing GitHub sha for ${path}`);
  return ghRequest(
    `https://api.github.com/repos/${owner}/${repo}/contents/${encodeURIComponent(path).replace(/%2F/g, "/")}`,
    {
      method: "PUT",
      headers: githubHeaders(ghToken),
      body: JSON.stringify({
        message,
        content: Buffer.from(content, "utf8").toString("base64"),
        sha,
        branch: ref,
      }),
    }
  );
}

// ── directory JSON update ─────────────────────────────────────────────────────

async function markVerifiedInJson(companyName, today, ghToken, owner, repo) {
  const filePath = "crm/directory_companies.json";
  const file     = await ghGet(filePath, ghToken, owner, repo);
  if (!file.content) return false;

  const companies = JSON.parse(Buffer.from(file.content, "base64").toString("utf8"));
  const idx = companies.findIndex(
    c => c.name && c.name.toLowerCase() === companyName.toLowerCase()
  );

  if (idx === -1) {
    // Not in directory yet — add a minimal entry so it can be rendered
    companies.push({ name: companyName, verified: true, verified_date: today });
  } else {
    companies[idx].verified      = true;
    companies[idx].verified_date = today;
  }

  await ghPut(
    filePath,
    JSON.stringify(companies, null, 2) + "\n",
    file.sha,
    `crm: mark ${companyName} as verified listing`,
    ghToken, owner, repo
  );
  return true;
}

// ── providers HTML badge update ───────────────────────────────────────────────

async function patchProviderBadge(companyName, ghToken, owner, repo) {
  const filePath = "site/providers/index.html";
  const file     = await ghGet(filePath, ghToken, owner, repo);
  if (!file.content) return false;

  let html = Buffer.from(file.content, "base64").toString("utf8");

  // Find the provider-card that contains this company name and update its badge
  // The card structure has: <div class="provider-name">CompanyName</div>
  // followed (within ~300 chars) by: <span class="provider-badge badge-trusted">Listed</span>
  const escapedName = companyName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(
    `(<div class="provider-name">${escapedName}<\\/div>[\\s\\S]{0,400}?)`  +
    `<span class="provider-badge badge-trusted">Listed<\\/span>`,
    "i"
  );

  if (!pattern.test(html)) return false;

  const patched = html.replace(
    pattern,
    `$1<span class="provider-badge badge-verified">✓ Verified</span>`
  );

  if (patched === html) return false;

  await ghPut(
    filePath,
    patched,
    file.sha,
    `site: verified badge for ${companyName}`,
    ghToken, owner, repo
  );
  return true;
}

// ── response pages ────────────────────────────────────────────────────────────

function yesPage(companyName) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>You're Listed — Robinhood Adjusting</title>
<style>
  body { margin:0; padding:0; background:#f5f5f5; font-family:Georgia,serif; }
  .wrap { max-width:560px; margin:60px auto; background:#fff; border-top:5px solid #c9922a; padding:48px 40px; text-align:center; }
  h1 { color:#0f2d4a; font-size:26px; margin:0 0 16px; }
  p { color:#444; font-size:16px; line-height:1.7; margin:0 0 20px; }
  .highlight { background:#e8f5e9; border-left:4px solid #1a6e3a; padding:14px 18px; text-align:left; margin:24px 0; font-size:15px; color:#222; }
  .badge { display:inline-block; background:#e8f5e9; color:#1a6e3a; border-radius:100px; padding:4px 14px; font-family:Arial,sans-serif; font-size:13px; font-weight:bold; margin-bottom:20px; }
  a.btn { display:inline-block; background:#c41e3a; color:#fff; padding:12px 28px; text-decoration:none; border-radius:4px; font-family:Arial,sans-serif; font-size:14px; font-weight:bold; }
  .footer { color:#999; font-size:12px; margin-top:32px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>You're listed.</h1>
  <div class="badge">✓ Verified Provider</div>
  <div class="highlight"><strong>${companyName}</strong> has been added to our provider directory.</div>
  <p>Homeowners in Palm Beach County can now find you when they need a trusted referral. You'll also receive our daily Trade Professional Brief.</p>
  <p>Duncan will follow up personally when a referral matches your service area.</p>
  <a href="${SITE_URL}/providers" class="btn">View the Directory</a>
  <p class="footer">Duncan Littlejohn · Public Adjuster · Wellington, FL · 561-772-7528</p>
</div>
</body>
</html>`;
}

function noPage() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Got It — Robinhood Adjusting</title>
<style>
  body { margin:0; padding:0; background:#f5f5f5; font-family:Georgia,serif; }
  .wrap { max-width:560px; margin:60px auto; background:#fff; border-top:5px solid #0f2d4a; padding:48px 40px; text-align:center; }
  h1 { color:#0f2d4a; font-size:26px; margin:0 0 16px; }
  p { color:#444; font-size:16px; line-height:1.7; margin:0 0 20px; }
  .footer { color:#999; font-size:12px; margin-top:32px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Got it — no problem.</h1>
  <p>We won't reach out again about a listing. If you change your mind, you can always request a listing at <a href="${SITE_URL}/providers">${SITE_URL}/providers</a>.</p>
  <p class="footer">Duncan Littlejohn · Public Adjuster · Wellington, FL · 561-772-7528</p>
</div>
</body>
</html>`;
}

function errorPage(msg) {
  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Error</title></head>
<body style="font-family:Arial,sans-serif;max-width:500px;margin:60px auto;text-align:center;">
<h2>Something went wrong</h2><p>${msg}</p>
<p>Please email <a href="mailto:duncanlittlejohn727@gmail.com">duncanlittlejohn727@gmail.com</a> and we'll sort it out.</p>
</body></html>`;
}

// ── handler ───────────────────────────────────────────────────────────────────

export async function handler(event) {
  const params     = event.queryStringParameters || {};
  const companyId  = params.company_id  || "";
  const contactId  = params.contact_id  || "";
  const action     = (params.action     || "").toLowerCase();

  const hsToken  = (process.env.HUBSPOT_API_KEY || "").trim();
  const ghToken  = (process.env.GITHUB_TOKEN || "").trim();
  const ghOwner  = (process.env.GITHUB_OWNER || "duncan727-debug").trim();
  const ghRepo   = (process.env.GITHUB_REPO  || "-robinhood-adjusting").trim();

  if (!hsToken) {
    return { statusCode: 500, headers: { "Content-Type": "text/html" },
             body: errorPage("Server configuration error.") };
  }

  if (!["yes", "no"].includes(action)) {
    return { statusCode: 400, headers: { "Content-Type": "text/html" },
             body: errorPage("Invalid action.") };
  }

  // ── NO path ────────────────────────────────────────────────────────────────
  if (action === "no") {
    if (contactId) {
      await hs("PATCH", `/crm/v3/objects/contacts/${contactId}`,
               { properties: { hs_lead_status: "UNQUALIFIED" } }, hsToken);
    }
    await moveDealStage(companyId, "closedlost", hsToken);   // → Declined
    return { statusCode: 200, headers: { "Content-Type": "text/html" }, body: noPage() };
  }

  // ── YES path ───────────────────────────────────────────────────────────────

  // 1. Get company name from HubSpot
  let companyName = "";
  if (companyId) {
    const { data } = await hs("GET",
      `/crm/v3/objects/companies/${companyId}?properties=name`, undefined, hsToken);
    companyName = data?.properties?.name || "";
  }

  // 2. Update HubSpot contact status + enroll in service-provider newsletter list
  if (contactId) {
    await hs("PATCH", `/crm/v3/objects/contacts/${contactId}`,
             { properties: { hs_lead_status: "CONNECTED" } }, hsToken);
    await hs("POST", `/contacts/v1/lists/6/add`,
             { vids: [parseInt(contactId)] }, hsToken);
  }

  // 3. Update HubSpot company + move deal to Listed in Directory
  if (companyId) {
    await hs("PATCH", `/crm/v3/objects/companies/${companyId}`,
             { properties: { description: "listing_confirmed" } }, hsToken);
    await moveDealStage(companyId, "decisionmakerboughtin", hsToken);  // → Listed in Directory
  }

  // 4. Update GitHub directory JSON + HTML (best-effort — don't fail the response)
  const today = new Date().toISOString().split("T")[0];
  if (ghToken && ghOwner && ghRepo && companyName) {
    try {
      await markVerifiedInJson(companyName, today, ghToken, ghOwner, ghRepo);
      await patchProviderBadge(companyName, ghToken, ghOwner, ghRepo);
    } catch (e) {
      console.error("GitHub update failed:", e.message);
    }
  }

  return {
    statusCode: 200,
    headers: { "Content-Type": "text/html" },
    body: yesPage(companyName || "Your business"),
  };
}
