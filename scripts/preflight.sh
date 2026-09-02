#!/usr/bin/env bash
#
# Pre-demo check: is the deployment actually able to do the demo right now?
#
# Written because the failures that ruin a live demo are the quiet ones. The
# site loads, the notes list looks right, and then extraction returns nothing
# because a model was retired last week or yesterday's testing spent the day's
# quota. None of that shows up until someone presses the button, so this presses
# the button — including one real extraction, which costs one request against
# the quota and is the only check that proves the whole path.
#
# Usage:
#   scripts/preflight.sh                      # the deployed demo
#   scripts/preflight.sh http://localhost:8000  # a local backend
#
# Exit code is 0 only if every check passed.

set -uo pipefail

BASE="${1:-http://140.238.101.112}"
API="$BASE/api/v1"
ROLE_HEADER="X-Demo-Role: Admin"

pass=0
fail=0
warn=0

green() { printf '\033[32m%s\033[0m' "$1"; }
red() { printf '\033[31m%s\033[0m' "$1"; }
yellow() { printf '\033[33m%s\033[0m' "$1"; }

ok() { printf '  %s %s\n' "$(green PASS)" "$1"; pass=$((pass + 1)); }
no() { printf '  %s %s\n' "$(red FAIL)" "$1"; fail=$((fail + 1)); }
hm() { printf '  %s %s\n' "$(yellow WARN)" "$1"; warn=$((warn + 1)); }

echo "Pre-flight against $BASE"
echo

# ── 1. The page itself ──
echo "Site"
code=$(curl -s -o /tmp/preflight_index -w '%{http_code}' --max-time 15 "$BASE/")
if [ "$code" = "200" ] && grep -qi '<div id="root"' /tmp/preflight_index; then
  ok "index.html served"
else
  no "index.html — HTTP $code"
fi

asset=$(grep -o 'src="/assets/[^"]*\.js"' /tmp/preflight_index | head -1 | cut -d'"' -f2)
if [ -n "$asset" ]; then
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$BASE$asset")
  # A stale index.html pointing at a hash that no longer exists renders blank,
  # and it renders blank for the visitor rather than for whoever deployed it.
  [ "$code" = "200" ] && ok "JS bundle $asset" || no "JS bundle $asset — HTTP $code"
else
  no "no JS bundle referenced by index.html"
fi

# ── 2. API and data source ──
echo
echo "API"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$BASE/health")
[ "$code" = "200" ] && ok "health" || no "health — HTTP $code"

notes=$(curl -s --max-time 20 -H "$ROLE_HEADER" "$API/notes/?page_size=1")
total=$(printf '%s' "$notes" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("total",0))' 2>/dev/null || echo 0)
if [ "$total" -gt 0 ] 2>/dev/null; then
  ok "notes readable from the data source ($total notes)"
else
  no "no notes returned — data source unreachable or unseeded"
fi

filters=$(curl -s --max-time 20 -H "$ROLE_HEADER" "$API/notes/filters")
authors=$(printf '%s' "$filters" | python3 -c 'import sys,json;print(len(json.load(sys.stdin).get("authors",[])))' 2>/dev/null || echo 0)
[ "$authors" -gt 0 ] 2>/dev/null \
  && ok "filter options populated ($authors clinicians)" \
  || no "filter options empty — the browser's filters will be unusable"

# Role separation is part of what the demo claims. If it has quietly stopped
# working, better to find out now than while showing it.
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 -H "X-Demo-Role: ReadOnly" "$API/notes/?page_size=1")
[ "$code" = "403" ] && ok "ReadOnly is refused note access (403)" \
  || hm "ReadOnly got HTTP $code, expected 403"

# ── 3. The model chain ──
echo
echo "AI models"
curl -s --max-time 20 -H "$ROLE_HEADER" "$API/extraction/models" -o /tmp/preflight_chain.json
python3 - /tmp/preflight_chain.json <<'PY'
import json
import sys

try:
    with open(sys.argv[1]) as handle:
        models = json.load(handle)
except (json.JSONDecodeError, OSError):
    print("  could not read the model chain")
    raise SystemExit(2)

if not models:
    print("  chain is empty — no provider is configured")
    raise SystemExit(2)

available = 0
for m in models:
    mark = "*" if m["is_primary"] else " "
    label = f"{m['provider']}:{m['model']}"
    if m["available"]:
        available += 1
        print(f"       {mark} {label:38} available")
    else:
        wait = m.get("available_in_seconds") or 0
        print(f"       {mark} {label:38} {m.get('reason')} ({int(wait // 60)}m)")

raise SystemExit(0 if available else 2)
PY
chain_status=$?
if [ "$chain_status" -eq 0 ]; then
  ok "at least one model is available"
else
  no "no model is available — extraction will fail"
fi

# ── 4. One real extraction ──
# The only check that exercises prompt, provider, parsing and provenance
# together. Everything above can pass while this fails.
echo
echo "Extraction"
curl -s --max-time 120 -X POST "$API/extraction/from-text" \
  -H 'Content-Type: application/json' -H "$ROLE_HEADER" \
  -d '{"text":"72y woman admitted with community-acquired pneumonia. Commenced amoxicillin 500mg TDS.","columns":[{"name":"Diagnosis","data_type":"text","description":"Primary diagnosis"},{"name":"Medication","data_type":"text","description":"Drug started"}],"source_name":"preflight"}' \
  -o /tmp/preflight_extraction.json

python3 - /tmp/preflight_extraction.json <<'PY'
import json
import sys

try:
    with open(sys.argv[1]) as handle:
        raw = handle.read()
except OSError:
    raw = ""
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print(f"       unreadable response: {raw[:200]}")
    raise SystemExit(2)

if "detail" in data:
    print(f"       {data['detail'][:300]}")
    raise SystemExit(2)

rows = data.get("rows") or []
if not rows:
    print("       returned no rows")
    raise SystemExit(2)

print(f"       {json.dumps(rows[0], ensure_ascii=False)[:160]}")
# A row that came back without the diagnosis means the model answered but the
# extraction is not actually working, which looks the same from the outside.
raise SystemExit(0 if any("pneumonia" in str(v).lower() for v in rows[0].values()) else 3)
PY
case $? in
  0) ok "live extraction returned the expected data" ;;
  3) hm "extraction returned rows, but not the expected diagnosis — check quality" ;;
  *) no "live extraction failed" ;;
esac

# ── 5. The review gate ──
# The extraction above was persisted as a draft run. That is the claim the whole
# workflow rests on — nothing leaves as reviewed data until a clinician signs it
# — so check it on the deployment rather than trusting the unit tests.
echo
echo "Review and sign-off"
run_id=$(python3 -c '
import json, sys
try:
    print(json.load(open("/tmp/preflight_extraction.json")).get("run_id", ""))
except Exception:
    print("")
')

if [ -n "$run_id" ]; then
  status=$(curl -s --max-time 20 -H "$ROLE_HEADER" "$API/runs/$run_id" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status",""))' 2>/dev/null || echo "")
  [ "$status" = "draft" ] \
    && ok "the extraction was saved as a draft run" \
    || no "run $run_id came back as '$status', expected draft"

  # An unreviewed run must not export as approved data.
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 -H "$ROLE_HEADER" \
    "$API/export/runs/$run_id/csv?scope=approved")
  [ "$code" = "409" ] \
    && ok "export of approved rows is refused while none are approved (409)" \
    || no "approved-rows export returned HTTP $code, expected 409 — the review gate is open"

  # A draft may still be exported, but only labelled as a draft.
  name=$(curl -s -D - -o /dev/null --max-time 20 -H "$ROLE_HEADER" \
    "$API/export/runs/$run_id/csv?scope=all" | grep -i 'content-disposition' || echo "")
  case "$name" in
    *DRAFT*) ok "draft export is labelled DRAFT" ;;
    *) no "draft export was not labelled: $name" ;;
  esac

  # Leave nothing behind: a pre-flight run is not someone's work to review.
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 -X DELETE \
    -H "$ROLE_HEADER" "$API/runs/$run_id")
  [ "$code" = "204" ] \
    && ok "pre-flight run discarded" \
    || hm "could not discard the pre-flight run (HTTP $code) — it will sit in the review queue"
else
  no "the extraction response carried no run id — results are not being persisted"
fi

# ── Summary ──
echo
if [ "$fail" -eq 0 ] && [ "$warn" -eq 0 ]; then
  echo "$(green "All $pass checks passed") — the demo is ready."
elif [ "$fail" -eq 0 ]; then
  echo "$(green "$pass passed"), $(yellow "$warn warning(s)") — usable, but look at the warnings."
else
  echo "$(green "$pass passed"), $(yellow "$warn warning(s)"), $(red "$fail failed") — fix before demoing."
fi
exit $((fail > 0 ? 1 : 0))
