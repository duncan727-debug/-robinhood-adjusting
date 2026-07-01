// Read-only GitHub connection check for Netlify.
//
// Required env vars:
//   GITHUB_TOKEN - fine-grained token with repository Contents read/write
//   GITHUB_OWNER - defaults to duncan727-debug
//   GITHUB_REPO  - defaults to -robinhood-adjusting
//   GITHUB_REF   - defaults to main

const GITHUB_API_VERSION = "2022-11-28";
const DEFAULT_OWNER = "duncan727-debug";
const DEFAULT_REPO = "-robinhood-adjusting";
const DEFAULT_REF = "main";

function json(statusCode, body) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
    body: JSON.stringify(body, null, 2),
  };
}

function env(name, fallback = "") {
  return (process.env[name] || fallback).trim();
}

function githubHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "User-Agent": "robinhood-adjusting-netlify",
    "X-GitHub-Api-Version": GITHUB_API_VERSION,
  };
}

async function githubGet(path, token) {
  const res = await fetch(`https://api.github.com${path}`, {
    headers: githubHeaders(token),
  });
  const text = await res.text();
  let data = {};
  if (text) {
    try { data = JSON.parse(text); } catch (_) { data = { raw: text }; }
  }
  if (!res.ok) {
    const message = data.message || res.statusText || "GitHub API request failed";
    throw new Error(`GitHub ${res.status}: ${message}`);
  }
  return data;
}

exports.handler = async function () {
  const token = env("GITHUB_TOKEN");
  const owner = env("GITHUB_OWNER", DEFAULT_OWNER);
  const repo = env("GITHUB_REPO", DEFAULT_REPO);
  const ref = env("GITHUB_REF", DEFAULT_REF);

  if (!token) {
    return json(500, {
      ok: false,
      error: "Missing GITHUB_TOKEN",
      expectedEnv: ["GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO", "GITHUB_REF"],
    });
  }

  try {
    const encodedRepo = encodeURIComponent(repo);
    const encodedRef = encodeURIComponent(ref);
    const repoData = await githubGet(`/repos/${owner}/${encodedRepo}`, token);
    const checks = {};

    for (const file of ["crm/directory_companies.json", "site/providers/index.html"]) {
      const encodedFile = encodeURIComponent(file).replace(/%2F/g, "/");
      const data = await githubGet(
        `/repos/${owner}/${encodedRepo}/contents/${encodedFile}?ref=${encodedRef}`,
        token
      );
      checks[file] = {
        ok: true,
        sha: data.sha,
        size: data.size,
      };
    }

    return json(200, {
      ok: true,
      repo: repoData.full_name,
      defaultBranch: repoData.default_branch,
      ref,
      permissions: repoData.permissions || null,
      checks,
    });
  } catch (err) {
    return json(502, {
      ok: false,
      owner,
      repo,
      ref,
      error: err.message,
    });
  }
};
