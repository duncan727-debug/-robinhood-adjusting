#!/usr/bin/env python3
"""One-shot: create Partner Outreach deals at 'Outreach Sent' for the 35 staged
follow-ups (Chamber 5/19 + 9 refreshed + 20 research). Idempotent: skips contacts
that already have a deal in the 'default' pipeline.

For contacts whose draft is still in [Gmail]/Drafts: pre-creates the deal so the
pipeline reflects the staged-but-unsent state.
For contacts whose draft has been sent today: creates the deal with today's
timestamp (close enough — actual send time isn't critical for stage tracking).
"""
import os, json, imaplib, email, urllib.request, time
from pathlib import Path

for line in Path("config/.secrets").read_text().splitlines():
    if line.startswith("export "): line = line[7:]
    if "=" in line:
        k,v = line.split("=",1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TOK = os.environ["HUBSPOT_API_KEY"]
GMAIL_USER = "duncanlittlejohn727@gmail.com"
GMAIL_PWD = os.environ["GMAIL_APP_PASSWORD"]
PIPELINE = "default"
STAGE_SENT = "qualifiedtobuy"  # "Outreach Sent"


def api(path, body=None, method=None):
    method = method or ("POST" if body else "GET")
    req = urllib.request.Request(f"https://api.hubapi.com{path}",
        data=json.dumps(body).encode() if body else None, method=method,
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def list_draft_recipients():
    imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    imap.login(GMAIL_USER, GMAIL_PWD)
    imap.select('"[Gmail]/Drafts"', readonly=True)
    _, data = imap.search(None, "ALL")
    addrs = set()
    for i in data[0].split():
        _, d = imap.fetch(i, "(BODY.PEEK[HEADER.FIELDS (TO)])")
        msg = email.message_from_bytes(d[0][1])
        to = (msg.get("To") or "").strip().lower()
        if to: addrs.add(to)
    imap.logout()
    return addrs


def get_associated_company(cid):
    try:
        r = api(f"/crm/v4/objects/contacts/{cid}/associations/companies")
        results = r.get("results", [])
        return results[0]["toObjectId"] if results else None
    except Exception:
        return None


def existing_deal(cid):
    """Return deal id if contact already has any deal in default pipeline, else None."""
    try:
        r = api(f"/crm/v4/objects/contacts/{cid}/associations/deals")
        for assoc in r.get("results", []):
            did = assoc["toObjectId"]
            d = api(f"/crm/v3/objects/deals/{did}?properties=pipeline,dealstage")
            if d["properties"].get("pipeline") == PIPELINE:
                return did
    except Exception:
        pass
    return None


def create_deal(name, cid, company_id):
    payload = {
        "properties": {
            "dealname": name,
            "pipeline": PIPELINE,
            "dealstage": STAGE_SENT,
        },
        "associations": [
            {"to": {"id": cid}, "types": [{"associationCategory":"HUBSPOT_DEFINED","associationTypeId": 3}]}
        ]
    }
    if company_id:
        payload["associations"].append(
            {"to": {"id": company_id}, "types": [{"associationCategory":"HUBSPOT_DEFINED","associationTypeId": 5}]}
        )
    return api("/crm/v3/objects/deals", payload)["id"]


def load_targets():
    # 20 research
    targets = []
    for r in json.load(open("/tmp/_deal_targets_research.json")):
        targets.append({"name": r["name"], "to": r["to"].lower(), "cid": r["cid"], "src": "research"})
    # 9 chamber-refresh (contact_ids in batch file)
    for r in json.load(open("scripts/_chamber-style-refresh-batch.json")):
        targets.append({"name": r["name"], "to": r["to"].lower(), "cid": str(r["contact_id"]), "src": "refresh"})
    # 6 Chamber 5/19 list 11
    chamber = [
        ("Ileana Williams","iwilliams@ithinkfi.org","488459244235"),
        ("Peter Plaza","drpete@myhopehealth.com","488462854901"),
        ("Ana Alegre","ana@cpbchamber.com","488462858985"),
        ("Mary Lou Bedford","marylou@cpbchamber.com","488484481744"),
        ("Louis Eisenberg","louis.eisenberg@dortfcu.org","488502345434"),
        ("Amelia Jadoo","amelia@anchorexecllc.com","488506057435"),
    ]
    for n,e,c in chamber:
        targets.append({"name": n, "to": e.lower(), "cid": c, "src": "chamber"})
    return targets


def main():
    print("== Reading Gmail Drafts folder")
    drafts = list_draft_recipients()
    print(f"  {len(drafts)} drafts present")

    targets = load_targets()
    print(f"== {len(targets)} target contacts")

    created = skipped = errored = 0
    for t in targets:
        cid = t["cid"]
        if not cid:
            print(f"  - {t['name']}: no contact_id, skip"); errored += 1; continue

        existing = existing_deal(cid)
        if existing:
            print(f"  ~ {t['name']}: deal {existing} already exists, skip"); skipped += 1; continue

        still_drafted = t["to"] in drafts
        state = "STAGED" if still_drafted else "SENT"
        company_id = get_associated_company(cid)

        dealname = f"Outreach — {t['name']}"
        try:
            did = create_deal(dealname, cid, company_id)
            print(f"  + {t['name']} ({state}): deal {did} (company {company_id})")
            created += 1
        except urllib.error.HTTPError as e:
            print(f"  ! {t['name']}: HTTP {e.code} {e.read()[:200]}"); errored += 1

    print(f"\nCreated: {created}  Skipped: {skipped}  Errored: {errored}")


if __name__ == "__main__":
    main()
