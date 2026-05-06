// Netlify function: capture multiple-choice qualifying answer → HubSpot
// Called via link click from drip email: ?email=EMAIL&answer=ANSWER_CODE
//
// Updates HubSpot contact property 'qualifying_answer' and returns a thank-you page.

const ANSWER_LABELS = {
  // Homeowner answers
  "open-claim":           "Open claim in progress",
  "denied-claim":         "Denied or underpaid claim",
  "filing-claim":         "About to file a claim",
  "preparing":            "No active claim — staying informed",
  // Service provider answers
  "homeowner-referrals":  "Looking for homeowner referrals",
  "pa-partnership":       "Looking to refer clients with claims",
  "both":                 "Looking for both referrals and partnerships",
  "directory-listing":    "Directory listing and market intelligence",
  // Real estate answers
  "frequent":             "Insurance issues come up frequently",
  "occasional":           "Insurance issues come up occasionally",
  "active-situation":     "Active client situation right now",
  "rare":                 "Insurance issues rarely or never come up",
};

const SITE_URL = "https://robinhoodadjusting.com";

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

function thankYouPage(answerLabel) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Got it — Robinhood Adjusting</title>
<style>
  body { margin: 0; padding: 0; background: #f5f5f5; font-family: Georgia, 'Times New Roman', serif; }
  .wrap { max-width: 560px; margin: 60px auto; background: #fff; border-top: 5px solid #c9922a; padding: 48px 40px; text-align: center; }
  h1 { color: #0f2d4a; font-size: 26px; margin: 0 0 16px; }
  p { color: #444; font-size: 16px; line-height: 1.7; margin: 0 0 24px; }
  .answer { background: #f8f4ee; border-left: 4px solid #c41e3a; padding: 14px 18px; text-align: left; margin: 24px 0; font-size: 15px; color: #222; }
  a.btn { display: inline-block; background: #c41e3a; color: #fff; padding: 12px 28px; text-decoration: none; border-radius: 4px; font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; }
  .footer { color: #999; font-size: 12px; margin-top: 32px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Got it — thank you.</h1>
  <p>Your answer has been recorded:</p>
  <div class="answer"><strong>${answerLabel}</strong></div>
  <p>I'll make sure the information I send you is relevant to where you are.<br>If anything urgent comes up, you can always reach me directly.</p>
  <a href="${SITE_URL}" class="btn">Visit Robinhood Adjusting</a>
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
<h2>Something went wrong</h2>
<p>${message}</p>
<p><a href="${SITE_URL}" style="color:#c41e3a;">Return to robinhoodadjusting.com</a></p>
</body>
</html>`;
}

exports.handler = async function (event) {
  if (event.httpMethod !== "GET") {
    return { statusCode: 405, body: "Method not allowed" };
  }

  const token = (process.env.HUBSPOT_API_KEY || "").trim();
  if (!token) {
    return {
      statusCode: 500,
      headers: { "Content-Type": "text/html" },
      body: errorPage("Configuration error. Please contact us directly."),
    };
  }

  const params = event.queryStringParameters || {};
  const email  = (params.email  || "").trim().toLowerCase();
  const answer = (params.answer || "").trim();

  if (!email || !answer) {
    return {
      statusCode: 400,
      headers: { "Content-Type": "text/html" },
      body: errorPage("Invalid link — missing email or answer."),
    };
  }

  const answerLabel = ANSWER_LABELS[answer];
  if (!answerLabel) {
    return {
      statusCode: 400,
      headers: { "Content-Type": "text/html" },
      body: errorPage("Unrecognized answer. Please reply to your email instead."),
    };
  }

  const hs = makeHs(token);

  // Look up contact by email
  const search = await hs("POST", "/crm/v3/objects/contacts/search", {
    filterGroups: [{ filters: [{ propertyName: "email", operator: "EQ", value: email }] }],
    properties: ["email", "qualifying_answer"],
    limit: 1,
  });

  if (!search.data.results || search.data.results.length === 0) {
    // Contact not found — still show thank-you (link may be forwarded, etc.)
    return {
      statusCode: 200,
      headers: { "Content-Type": "text/html" },
      body: thankYouPage(answerLabel),
    };
  }

  const contactId = search.data.results[0].id;

  await hs("PATCH", `/crm/v3/objects/contacts/${contactId}`, {
    properties: { qualifying_answer: `${answer}|${answerLabel}` },
  });

  return {
    statusCode: 200,
    headers: { "Content-Type": "text/html" },
    body: thankYouPage(answerLabel),
  };
};
