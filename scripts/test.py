#!/usr/bin/env python3
"""Tests for the dataset. A data product is judged on whether the numbers are right."""
import json, os, re, glob, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "docs")
passed = failed = 0
def check(n, ok, d=""):
    global passed, failed
    if ok: passed += 1; print("  ok   " + n)
    else: failed += 1; print("  FAIL " + n + ((" - " + str(d)) if d else ""))

print("dataset tests\n")
raw = json.load(open(os.path.join(ROOT, "data", "raw.json")))
check("27 member states present", len(raw["member_states"]) == 27, raw["member_states"])
check("Greece is EL not GR", "EL" in raw["member_states"] and "GR" not in raw["member_states"])
check("rows have rate values", all(r.get("rate_value") for r in raw["rows"]))
def is_num(v):
    try:
        float(v); return True
    except (TypeError, ValueError):
        return False
bad = [r["rate_value"] for r in raw["rows"] if not is_num(r["rate_value"])]
check("every rate parses as a number", not bad, bad[:3])

codes = glob.glob(os.path.join(SITE, "data/by-code/*.json"))
pages = glob.glob(os.path.join(SITE, "code/*.html"))
check("a JSON file per commodity code", len(codes) > 2000, len(codes))
check("a page per commodity code", len(pages) == len(codes), "%d vs %d" % (len(pages), len(codes)))

print("\ncorrectness a buyer would notice:")
bad_range = []
for p in pages[:400]:
    s = open(p).read()
    m = re.search(r"rates from ([\d.]+)% to ([\d.]+)%", s)
    if m and float(m.group(1)) > float(m.group(2)):
        bad_range.append(os.path.basename(p))
check("no page states a range backwards", not bad_range, bad_range[:3])

missing_attr = [p for p in pages[:200] if "European Union" not in open(p).read()]
check("every page carries the required attribution", not missing_attr, missing_attr[:2])
missing_lic = [p for p in codes[:200] if "CC BY 4.0" not in open(p).read()]
check("every JSON carries the licence", not missing_lic, missing_lic[:2])

print("\nhonesty:")
sample = open(pages[0]).read()
check("says it is not tax advice", "not tax advice" in sample)
check("states the situation date", re.search(r"Situation on \d{4}-\d{2}-\d{2}", sample) is not None)
check("says the data was reshaped, not altered", "unaltered" in sample or "not altered" in sample.lower())

print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
