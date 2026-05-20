#!/usr/bin/env python3
"""
hubspot_task.py — create a HubSpot task assigned to Duncan, optionally linked to a
company, contact, or deal.

USAGE
  ./hubspot_task.py --subject "..." --body "..." [--due YYYY-MM-DD]
                    [--priority HIGH|MEDIUM|LOW] [--type TODO|CALL|EMAIL]
                    [--company-id ID] [--contact-id ID] [--deal-id ID]
                    [--company-name "Acme Inc"]  # auto-resolves to company-id

The script reads HUBSPOT_API_KEY from environment or config/.secrets, finds Duncan's
owner ID by email, and POSTs to /crm/v3/objects/tasks. Returns the task ID on stdout.

Designed for use by automation: any time a workflow surfaces a Duncan-action item,
call this script and the task lands in his HubSpot inbox.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")


def get_token():
    token = os.environ.get("HUBSPOT_API_KEY", "").strip()
    if token:
        return token
    secrets = WORKSPACE / "config" / ".secrets"
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            if "HUBSPOT_API_KEY=" in line and not line.strip().startswith("#"):
                val = line.split("HUBSPOT_API_KEY=", 1)[1].strip().strip('"').strip("'")
                if val.startswith("pat-"):
                    return val
    sys.exit("ERROR: HUBSPOT_API_KEY not set in env and not in config/.secrets")


TOKEN = get_token()


def hs_request(method, path, payload=None, retries=3):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = {}
            try:
                body = json.loads(e.read())
            except Exception:
                pass
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            return e.code, body
    return 0, {"error": "max retries exceeded"}


def get_duncan_owner_id():
    status, data = hs_request("GET", "/crm/v3/owners?limit=50")
    if status == 200 and data.get("results"):
        for owner in data["results"]:
            if "duncan" in owner.get("email", "").lower():
                return owner["id"]
        return data["results"][0]["id"]
    return None


def find_company_id_by_name(name):
    status, data = hs_request("POST", "/crm/v3/objects/companies/search", {
        "filterGroups": [{"filters": [{"propertyName": "name", "operator": "EQ", "value": name}]}],
        "properties": ["name"],
        "limit": 1,
    })
    if status == 200 and data.get("results"):
        return data["results"][0]["id"]
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--subject", required=True, help="Task subject (title)")
    p.add_argument("--body", required=True, help="Task body / details")
    p.add_argument("--due", help="Due date YYYY-MM-DD (default: tomorrow)")
    p.add_argument("--priority", choices=["HIGH", "MEDIUM", "LOW"], default="MEDIUM")
    p.add_argument("--type", dest="task_type", choices=["TODO", "CALL", "EMAIL"], default="TODO")
    p.add_argument("--company-id", help="Associate with this HubSpot company ID")
    p.add_argument("--contact-id", help="Associate with this HubSpot contact ID")
    p.add_argument("--deal-id", help="Associate with this HubSpot deal ID")
    p.add_argument("--company-name", help="Resolve to company-id by exact name match")
    p.add_argument("--quiet", action="store_true", help="Only print task ID")
    args = p.parse_args()

    # Resolve due date → ms timestamp at 9am EDT that day
    if args.due:
        due_dt = datetime.strptime(args.due, "%Y-%m-%d")
    else:
        due_dt = datetime.utcnow() + timedelta(days=1)
    # Set to 9am EDT (=13:00 UTC, ignoring DST nuance for task ms)
    due_ts = int(due_dt.replace(hour=13, minute=0, second=0, microsecond=0,
                                tzinfo=timezone.utc).timestamp() * 1000)

    owner_id = get_duncan_owner_id()
    if not owner_id and not args.quiet:
        print("WARN: no Duncan owner found; task will be unassigned", file=sys.stderr)

    props = {
        "hs_task_subject": args.subject,
        "hs_task_body": args.body,
        "hs_task_status": "NOT_STARTED",
        "hs_task_type": args.task_type,
        "hs_task_priority": args.priority,
        "hs_timestamp": due_ts,
    }
    if owner_id:
        props["hubspot_owner_id"] = owner_id

    status, data = hs_request("POST", "/crm/v3/objects/tasks", {"properties": props})
    if status not in (200, 201):
        print(f"ERROR: task create failed status={status} body={data}", file=sys.stderr)
        sys.exit(2)
    task_id = data["id"]

    # Resolve company-name if given
    company_id = args.company_id
    if not company_id and args.company_name:
        company_id = find_company_id_by_name(args.company_name)
        if not company_id and not args.quiet:
            print(f"WARN: company '{args.company_name}' not found in HubSpot", file=sys.stderr)

    # Associations (PUT to /associations/<obj>/<id>/<association_type>)
    if company_id:
        hs_request("PUT", f"/crm/v3/objects/tasks/{task_id}/associations/companies/{company_id}/task_to_company", None)
    if args.contact_id:
        hs_request("PUT", f"/crm/v3/objects/tasks/{task_id}/associations/contacts/{args.contact_id}/task_to_contact", None)
    if args.deal_id:
        hs_request("PUT", f"/crm/v3/objects/tasks/{task_id}/associations/deals/{args.deal_id}/task_to_deal", None)

    if args.quiet:
        print(task_id)
    else:
        print(f"created task {task_id} | subject='{args.subject}' due={due_dt.date()} priority={args.priority}")


if __name__ == "__main__":
    main()
