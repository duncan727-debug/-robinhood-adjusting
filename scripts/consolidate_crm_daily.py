#!/usr/bin/env python3
"""
Daily CRM Research Consolidation for HubSpot Import
Consolidates all prospect research from daily drafts into a master CSV
Ready for direct upload to HubSpot (not paste)
"""

import csv
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

crm_dir = Path("/Users/victoria/.openclaw/workspace/crm")

# Load existing organizations and interactions data
organizations = {}
interactions = defaultdict(list)

# Read organizations.csv
org_csv_path = crm_dir / "organizations.csv"
if org_csv_path.exists():
    with open(org_csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            org_id = row['org_id']
            organizations[org_id] = row

# Read interactions.csv to understand contact history
int_csv_path = crm_dir / "interactions.csv"
if int_csv_path.exists():
    with open(int_csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            org_id = row['org_id']
            interactions[org_id].append(row)

print(f"Loaded {len(organizations)} organizations from CSV")
print(f"Loaded {len(interactions)} interaction records")

# Parse all markdown files from drafts to find additional prospects not in organizations.csv
additional_prospects = defaultdict(dict)

def parse_prospect_md(filepath):
    """Extract contact and company info from markdown draft"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Skip metadata files
        if 'SUMMARY' in filepath.name or 'BATCH' in filepath.name:
            return None

        filename = filepath.stem
        parts = filename.split('-', 1)
        if len(parts) < 2:
            return None

        county = parts[0]
        company_info = parts[1]

        # Extract company name (usually in Subject line)
        subject_match = re.search(r'Subject: Partnership Opportunity.*?at\s+([^,\n]+)', content)
        company_name = subject_match.group(1).strip() if subject_match else None

        # Extract contact name (from "Hi ," line)
        hi_match = re.search(r'^Hi\s+([^,]+),', content, re.MULTILINE)
        contact_name = hi_match.group(1).strip() if hi_match else None

        # Extract phone
        phone_match = re.search(r'(?:\+?1[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})', content)
        phone = f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}" if phone_match else None

        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]*\w+\.\w+', content)
        email = email_match.group(0) if email_match else None

        return {
            'company_name': company_name,
            'contact_name': contact_name,
            'email': email,
            'phone': phone,
            'county': county,
            'filename': filename
        }
    except:
        return None

drafts_dir = crm_dir / "drafts"
new_prospects = []

for date_folder in sorted(drafts_dir.iterdir()):
    if date_folder.is_dir() and date_folder.name.startswith('2026'):
        for md_file in date_folder.glob("*.md"):
            data = parse_prospect_md(md_file)
            if data:
                new_prospects.append(data)

print(f"\nFound {len(new_prospects)} unique prospect records from markdown drafts")

# Create master HubSpot import CSV combining all sources
timestamp = datetime.now().strftime('%Y-%m-%d')
output_file = crm_dir / f"hubspot_master_import_{timestamp}.csv"

with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'company_name', 'contact_email', 'contact_name', 'phone',
        'county', 'category', 'website', 'first_contact_date', 'status'
    ])
    writer.writeheader()

    # Write all organizations from existing CSV
    for org_id, org_data in organizations.items():
        writer.writerow({
            'company_name': org_data.get('name', ''),
            'contact_email': org_data.get('contact_email', ''),
            'contact_name': org_data.get('contact_name', ''),
            'phone': org_data.get('contact_phone', ''),
            'county': org_data.get('county', '').replace('-', ' ').title(),
            'category': org_data.get('category', ''),
            'website': org_data.get('website', ''),
            'first_contact_date': org_data.get('created_date', ''),
            'status': org_data.get('status', 'initial')
        })

    # Add new prospects from markdown (dedup by company name)
    existing_names = {org['name'].lower() for org in organizations.values()}
    added = 0

    for prospect in new_prospects:
        if prospect['company_name'] and prospect['company_name'].lower() not in existing_names:
            writer.writerow({
                'company_name': prospect['company_name'],
                'contact_email': prospect['email'] or '',
                'contact_name': prospect['contact_name'] or '',
                'phone': prospect['phone'] or '',
                'county': prospect['county'].replace('-', ' ').title(),
                'category': '',
                'website': '',
                'first_contact_date': datetime.now().strftime('%Y-%m-%d'),
                'status': 'new_research'
            })
            added += 1
            existing_names.add(prospect['company_name'].lower())

total_records = len(organizations) + added
print(f"\nWrote {len(organizations)} existing + {added} new = {total_records} total records")
print(f"Master import file saved to: {output_file}")

# Also update the main master file (without timestamp) for easy access
main_output = crm_dir / "hubspot_master_import.csv"
import shutil
shutil.copy(output_file, main_output)
print(f"Also updated: {main_output}")

print(f"\n✓ Daily HubSpot consolidation complete")
print(f"Ready for upload. Total records: {total_records}")
