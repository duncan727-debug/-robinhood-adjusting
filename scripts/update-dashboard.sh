#!/bin/bash
# Generates docs/dashboard-data.js from live workspace files.
# Run daily after ops-review, or manually any time.

set -euo pipefail
WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
TODAY=$(date +%Y-%m-%d)
DOW=$(date +%u)  # 1=Mon … 7=Sun

# ── Helper: status string ───────────────────────────────────────────────────
status() {
  # status <ok|warn|err|idle> <label> [detail]
  printf '{"s":"%s","label":"%s","detail":"%s"}' "$1" "$2" "${3:-}"
}

# ── Cron job checks ──────────────────────────────────────────────────────────
brief_status="err"; brief_detail="Not found"
[[ -f "$WORKSPACE/briefs/$TODAY.md" ]] && {
  lines=$(wc -l < "$WORKSPACE/briefs/$TODAY.md")
  brief_status="ok"; brief_detail="${lines} lines"
}

intel_status="err"; intel_detail="Not found"
[[ -d "$WORKSPACE/crm/intelligence/$TODAY" ]] && {
  count=$(ls "$WORKSPACE/crm/intelligence/$TODAY" 2>/dev/null | wc -l | tr -d ' ')
  intel_status="ok"; intel_detail="${count} profiles"
}

drafts_status="err"; drafts_detail="Not found"
draft_count=0
[[ -d "$WORKSPACE/crm/drafts/$TODAY" ]] && {
  draft_count=$(ls "$WORKSPACE/crm/drafts/$TODAY" 2>/dev/null | wc -l | tr -d ' ')
  drafts_status="ok"; drafts_detail="${draft_count} orgs staged"
}

responses_status="idle"; responses_detail="No folder"
[[ -d "$WORKSPACE/crm/responses/$TODAY" ]] && {
  rcount=$(ls "$WORKSPACE/crm/responses/$TODAY" 2>/dev/null | wc -l | tr -d ' ')
  responses_status="ok"; responses_detail="${rcount} processed"
}

opsreview_status="err"; opsreview_detail="Not found"
[[ -f "$WORKSPACE/ops-review/$TODAY.md" ]] && {
  opsreview_status="ok"; opsreview_detail="Generated"
}

hubspot_status="err"; hubspot_detail="No update today"
[[ -f "$WORKSPACE/crm/hubspot_master_import_$TODAY.csv" ]] && {
  hrows=$(wc -l < "$WORKSPACE/crm/hubspot_master_import_$TODAY.csv")
  hubspot_status="ok"; hubspot_detail="${hrows} rows ready"
}
# Also check upload log for today
grep -q "^$(date +%Y-%m-%d)" "$WORKSPACE/crm/hubspot_upload.log" 2>/dev/null && {
  hubspot_status="ok"; hubspot_detail="Uploaded today"
}

prospect_status="err"; prospect_detail="No data"
prospect_today=0
if [[ -f "$WORKSPACE/crm/api_usage.log" ]]; then
  api_line=$(grep "^$TODAY" "$WORKSPACE/crm/api_usage.log" 2>/dev/null | tail -1 || true)
  if [[ -n "$api_line" ]]; then
    prospect_today=$(echo "$api_line" | awk -F'calls: ' '{print $2}' | awk '{print $1}' || echo 0)
    if echo "$api_line" | grep -q "errors: 403\|error 403"; then
      prospect_status="err"; prospect_detail="API 403 error"
    elif [[ "$prospect_today" -gt 0 ]]; then
      prospect_status="ok"; prospect_detail="${prospect_today} added"
    else
      prospect_status="warn"; prospect_detail="0 contacts (check API)"
    fi
  fi
fi
# Fallback: check palm beach log for today
grep -q "$TODAY" "$WORKSPACE/crm/prospect_palm_beach.log" 2>/dev/null && {
  if grep "$TODAY" "$WORKSPACE/crm/prospect_palm_beach.log" | grep -q "403"; then
    prospect_status="err"; prospect_detail="API 403 error"
  fi
}

newsletter_status="warn"; newsletter_detail="Not sent"
[[ -f "$WORKSPACE/scripts/.newsletter-sent-$TODAY" ]] && {
  newsletter_status="ok"; newsletter_detail="Sent today"
}

trends_status="err"
latest_trend=$(ls "$WORKSPACE/content/trends/"*.md 2>/dev/null | sort | tail -1)
if [[ -n "$latest_trend" ]]; then
  trend_date=$(basename "$latest_trend" .md)
  days_ago=$(( ( $(date +%s) - $(date -j -f "%Y-%m-%d" "$trend_date" +%s 2>/dev/null || echo 0) ) / 86400 ))
  if [[ "$days_ago" -le 7 ]]; then
    trends_status="ok"; trends_detail="$trend_date"
  else
    trends_status="err"; trends_detail="Last: $trend_date (${days_ago}d ago)"
  fi
else
  trends_detail="No trends file found"
fi

rollup_status="idle"; rollup_detail="Fridays only"
if [[ "$DOW" -eq 5 ]]; then
  [[ -f "$WORKSPACE/weekly/$(date +%Y-W%V).md" ]] && {
    rollup_status="ok"; rollup_detail="Generated"
  } || { rollup_status="idle"; rollup_detail="Scheduled 5pm"; }
fi

# 4:30am daily content (blog + social)
content_status="err"; content_detail="Not found"
[[ -f "$WORKSPACE/content/$TODAY/blog.md" ]] && {
  content_status="ok"; content_detail="Generated"
}

# 6:30am website sync — any commit today that touches site/, briefs/, content/, or scripts/
websync_status="err"; websync_detail="Not synced"
today_commits=$(git -C "$WORKSPACE" log --since="$TODAY 00:00" --oneline --name-only 2>/dev/null)
if echo "$today_commits" | grep -qE "^(site/|briefs/|content/|scripts/)"; then
  commit_count=$(git -C "$WORKSPACE" log --since="$TODAY 00:00" --oneline 2>/dev/null | wc -l | tr -d ' ')
  websync_status="ok"; websync_detail="${commit_count} commits today"
fi

# 8:00am outreach batch 1
batch1_status="idle"; batch1_detail="Not run"
grep -q "^\[$TODAY.*[Bb]atch 1" "$WORKSPACE/scripts/outreach_send.log" 2>/dev/null && {
  sent=$(grep "^\[$TODAY.*[Bb]atch 1 done" "$WORKSPACE/scripts/outreach_send.log" 2>/dev/null | grep -o "sent: [0-9]*" | tail -1 | awk '{print $2}' || true)
  batch1_status="ok"; batch1_detail="${sent:-?} sent"
}

# 9:00am drip sequence
drip_status="idle"; drip_detail="Not run"
grep -q "^\[$TODAY" "$WORKSPACE/scripts/drip.log" 2>/dev/null && {
  drip_status="ok"; drip_detail="Run today"
}

# 10:00am enrichment gate
enrich_status="err"; enrich_detail="Not run"
grep -q "$TODAY" "$WORKSPACE/crm/email_enrichment.log" 2>/dev/null && {
  scraped=$(grep -A5 "=== Done ===" "$WORKSPACE/crm/email_enrichment.log" 2>/dev/null | grep "Scraped real email" | tail -1 | grep -o "[0-9]*" || echo "?")
  enrich_status="ok"; enrich_detail="${scraped} emails found"
}

# 10:30am outreach batch 2
batch2_status="idle"; batch2_detail="Not run"
grep -q "^\[$TODAY.*[Bb]atch 2" "$WORKSPACE/scripts/outreach_send.log" 2>/dev/null && {
  batch2_status="ok"; batch2_detail="Done"
}

# 10:45am contact form fallback
formfb_status="idle"; formfb_detail="Not run"
formfb_log="$WORKSPACE/scripts/contact_form_queue.log"
# Look for the agent's summary line which contains both "submitted=" and "blacklisted="
formfb_summary=$(grep "^\[$TODAY" "$formfb_log" 2>/dev/null | grep "submitted=" | grep "blacklisted=" | tail -1 || echo "")
if [[ -n "$formfb_summary" ]]; then
  submitted=$(echo "$formfb_summary" | grep -oE "submitted=[0-9]+" | grep -oE "[0-9]+" || echo 0)
  blacklisted=$(echo "$formfb_summary" | grep -oE "blacklisted=[0-9]+" | grep -oE "[0-9]+" || echo 0)
  formfb_status="ok"; formfb_detail="${submitted} submitted, ${blacklisted} skipped"
fi

# 11:00am linkedin sequencing
linkedin_status="idle"; linkedin_detail="Not run"
[[ -d "$WORKSPACE/crm/linkedin-queue/$TODAY" ]] && {
  lcount=$(ls "$WORKSPACE/crm/linkedin-queue/$TODAY" 2>/dev/null | wc -l | tr -d ' ')
  linkedin_status="ok"; linkedin_detail="${lcount} queued"
}

# 12:30pm outreach batch 3
batch3_status="idle"; batch3_detail="Not run"
grep -q "^\[$TODAY.*[Bb]atch 3" "$WORKSPACE/scripts/outreach_send.log" 2>/dev/null && {
  batch3_status="ok"; batch3_detail="Done"
}

# 1:00pm partnership network builder (Wednesdays)
ISOWEEK=$(date +%Y-W%V)
partner_status="idle"; partner_detail="Wednesdays only"
if [[ "$DOW" -eq 3 ]]; then
  [[ -d "$WORKSPACE/crm/partnerships/$ISOWEEK" ]] && {
    partner_status="ok"; partner_detail="Run today"
  } || { partner_status="warn"; partner_detail="Scheduled 1pm"; }
fi

# 3:00pm outreach batch 4
batch4_status="idle"; batch4_detail="Not run"
grep -q "^\[$TODAY.*[Bb]atch 4" "$WORKSPACE/scripts/outreach_send.log" 2>/dev/null && {
  batch4_status="ok"; batch4_detail="Done"
}

# ── Backlog count ────────────────────────────────────────────────────────────
backlog_count=0
for dir in "$WORKSPACE/crm/drafts"/*/; do
  dname=$(basename "$dir")
  [[ "$dname" < "$TODAY" ]] && backlog_count=$((backlog_count + $(ls "$dir" 2>/dev/null | wc -l | tr -d ' ')))
done

# ── Prospect pipeline total ──────────────────────────────────────────────────
seen_total=0
[[ -f "$WORKSPACE/crm/.prospect_state.json" ]] && {
  seen_total=$(python3 -c "import json; d=json.load(open('$WORKSPACE/crm/.prospect_state.json')); print(len(d.get('seen',[])))" 2>/dev/null || echo 0)
}

# ── Provider count ───────────────────────────────────────────────────────────
provider_count=0
[[ -f "$WORKSPACE/site/providers/index.html" ]] && {
  provider_count=$(grep -c 'provider-card\|class="card"' "$WORKSPACE/site/providers/index.html" 2>/dev/null || echo 62)
}
[[ "$provider_count" -eq 0 ]] && provider_count=62

# ── Health score (core operations only) ──────────────────────────────────────
ok_count=0; total_count=9
for s in "$brief_status" "$intel_status" "$drafts_status" "$opsreview_status" "$hubspot_status" "$prospect_status" "$newsletter_status" "$trends_status" "$websync_status"; do
  [[ "$s" == "ok" ]] && ok_count=$((ok_count + 1))
done
health_pct=$(( ok_count * 100 / total_count ))

# ── Cycle day ────────────────────────────────────────────────────────────────
start_epoch=$(date -j -f "%Y-%m-%d" "2026-04-22" +%s 2>/dev/null || date -d "2026-04-22" +%s 2>/dev/null || echo 0)
now_epoch=$(date +%s)
cycle_day=$(( (now_epoch - start_epoch) / 86400 + 1 ))
[[ "$cycle_day" -gt 100 ]] && cycle_day=100
[[ "$cycle_day" -lt 1 ]] && cycle_day=1

# ── Parse ops review for brief line count and key alerts ────────────────────
ops_brief_summary=""
ops_alerts=""
if [[ -f "$WORKSPACE/ops-review/$TODAY.md" ]]; then
  ops_brief_summary=$(grep "Brief generated:" "$WORKSPACE/ops-review/$TODAY.md" 2>/dev/null | head -1 | sed 's/.*Brief generated: //' | sed 's/[""]/\\"/g' | cut -c1-120 || true)
  ops_alerts=$(grep "^- \*\*[^*]" "$WORKSPACE/ops-review/$TODAY.md" 2>/dev/null | head -5 | sed 's/^- //' | sed 's/[""]/"/g' | tr '\n' '|' || true)
fi

# ── Write output ─────────────────────────────────────────────────────────────
cat > "$WORKSPACE/docs/dashboard-data.js" << JSEOF
// Auto-generated by update-dashboard.sh — $(date)
const DASHBOARD_DATA = {
  generated: "$(date '+%Y-%m-%d %H:%M %Z')",
  today: "$TODAY",
  cycleDay: $cycle_day,
  healthPct: $health_pct,

  kpis: {
    draftsReady: $draft_count,
    backlog: $backlog_count,
    prospectsTotal: $seen_total,
    prospectToday: $prospect_today,
    providerListings: $provider_count
  },

  crons: [
    { time:"4:00am",  name:"Daily Brief",         detail:$(printf '"%s"' "$brief_detail"),       status:"$brief_status" },
    { time:"4:30am",  name:"Content Generation",  detail:$(printf '"%s"' "$content_detail"),     status:"$content_status" },
    { time:"5:00am",  name:"Prospect Intel",       detail:$(printf '"%s"' "$intel_detail"),       status:"$intel_status" },
    { time:"5:45am",  name:"Newsletter",           detail:"Scheduled",                            status:"idle" },
    { time:"6:00am",  name:"CRM Drafts",           detail:$(printf '"%s"' "$drafts_detail"),      status:"$drafts_status" },
    { time:"6:30am",  name:"Website Sync",         detail:$(printf '"%s"' "$websync_detail"),     status:"$websync_status" },
    { time:"7:00am",  name:"Response Handler",     detail:$(printf '"%s"' "$responses_detail"),   status:"$responses_status" },
    { time:"7:30am",  name:"Ops Review",           detail:$(printf '"%s"' "$opsreview_detail"),   status:"$opsreview_status" },
    { time:"8:00am",  name:"Outreach Batch 1",     detail:$(printf '"%s"' "$batch1_detail"),      status:"$batch1_status" },
    { time:"8:30am",  name:"HubSpot Sync",         detail:$(printf '"%s"' "$hubspot_detail"),     status:"$hubspot_status" },
    { time:"9:00am",  name:"Prospecting",          detail:$(printf '"%s"' "$prospect_detail"),    status:"$prospect_status" },
    { time:"9:00am",  name:"Drip Sequence",        detail:$(printf '"%s"' "$drip_detail"),        status:"$drip_status" },
    { time:"10:00am", name:"Enrichment Gate",      detail:$(printf '"%s"' "$enrich_detail"),      status:"$enrich_status" },
    { time:"10:30am", name:"Outreach Batch 2",     detail:$(printf '"%s"' "$batch2_detail"),      status:"$batch2_status" },
    { time:"10:45am", name:"Contact Form Fallback",detail:$(printf '"%s"' "$formfb_detail"),      status:"$formfb_status" },
    { time:"11:00am", name:"LinkedIn Sequencing",  detail:$(printf '"%s"' "$linkedin_detail"),    status:"$linkedin_status" },
    { time:"12:30pm", name:"Outreach Batch 3",     detail:$(printf '"%s"' "$batch3_detail"),      status:"$batch3_status" },
    { time:"1:00pm",  name:"Partnership Builder",  detail:$(printf '"%s"' "$partner_detail"),     status:"$partner_status" },
    { time:"3:00pm",  name:"Outreach Batch 4",     detail:$(printf '"%s"' "$batch4_detail"),      status:"$batch4_status" },
    { time:"Sat 9am", name:"Trends (weekly)",      detail:$(printf '"%s"' "${trends_detail:-Not generated}"), status:"$trends_status" },
    { time:"5:00pm",  name:"Weekly Rollup",        detail:$(printf '"%s"' "$rollup_detail"),      status:"$rollup_status" }
  ],

  streams: {
    crm: {
      health: $([ "$drafts_status" = "ok" ] && echo '"good"' || echo '"warn"'),
      metric: "$draft_count",
      metricLabel: "ready to send",
      desc: "$([ $draft_count -gt 0 ] && echo "$draft_count orgs staged and personalized for $TODAY." || echo "No drafts generated yet today.") Backlog: $backlog_count unsent.",
      stats: [
        { label:"Today's Batch",  val:"${draft_count} orgs",  style:"$([ $draft_count -gt 0 ] && echo ok || echo err)" },
        { label:"Backlog",        val:"${backlog_count} unsent", style:"$([ $backlog_count -gt 20 ] && echo warn || echo ok)" },
        { label:"Follow-up Due",  val:"May 11–12",             style:"muted" },
        { label:"API Prospecting",val:"$([ "$prospect_status" = "ok" ] && echo "${prospect_today} today" || echo "Error")", style:"$prospect_status" }
      ]
    },
    newsletter: {
      health: "$([ "$newsletter_status" = "ok" ] && echo good || echo bad)",
      metric: "$([ "$newsletter_status" = "ok" ] && echo "✓" || echo "?")",
      metricLabel: "$([ "$newsletter_status" = "ok" ] && echo "sent today" || echo "delivery unknown")",
      desc: "$([ "$newsletter_status" = "ok" ] && echo "Newsletter sent today." || echo "No send confirmation for today. Check HubSpot campaign logs.")",
      stats: [
        { label:"Brief",    val:"$([ "$brief_status" = "ok" ] && echo "✓ Generated" || echo "Missing")",      style:"$brief_status" },
        { label:"Delivered",val:"$([ "$newsletter_status" = "ok" ] && echo "✓ Sent" || echo "Unconfirmed")", style:"$newsletter_status" },
        { label:"Trends",   val:"$([ "$trends_status" = "ok" ] && echo "✓ Current" || echo "Broken")",        style:"$trends_status" },
        { label:"Open Rate",val:"Check HubSpot",                                                               style:"muted" }
      ]
    },
    prospecting: {
      health: "$([ "$prospect_status" = "ok" ] && echo good || echo warn)",
      metric: "$seen_total",
      metricLabel: "total prospected",
      desc: "$([ "$prospect_status" = "ok" ] && echo "${prospect_today} contacts added today via Google Places API." || echo "API issue today — 0 contacts scraped. Check key/billing.") Running total: $seen_total.",
      stats: [
        { label:"Today's Pull",   val:"$([ "$prospect_status" = "ok" ] && echo "${prospect_today} added" || echo "0 (error)")", style:"$prospect_status" },
        { label:"Total Seen",     val:"${seen_total}",          style:"ok" },
        { label:"HubSpot Sync",   val:"$([ "$hubspot_status" = "ok" ] && echo "✓ Current" || echo "Silent")", style:"$hubspot_status" },
        { label:"API Cost/Day",   val:"\$0.034",                style:"ok" }
      ]
    }
  },

  alerts: [],

  links: {
    brief:    "$([ -f "$WORKSPACE/briefs/$TODAY.html" ] && echo "../briefs/$TODAY.html" || echo "../briefs/$TODAY.md")",
    drafts:   "../crm/drafts/$TODAY/",
    opsReview:"../ops-review/$TODAY.md",
    hubspot:  "https://app.hubspot.com",
    website:  "https://robinhoodadjusting.com",
    schedule: "../OPERATIONS-SCHEDULE.html"
  }
};
JSEOF

echo "[$(date '+%H:%M')] dashboard-data.js updated — health: ${health_pct}%, drafts: ${draft_count}, backlog: ${backlog_count}, cycle day: ${cycle_day}"
