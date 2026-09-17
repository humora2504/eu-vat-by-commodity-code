#!/usr/bin/env python3
"""Build the change feed by diffing today's pull against the last published one.

This is the thing that is actually worth paying for: not the data, which is free,
but a machine-readable answer to "what changed and does it affect me". A promise of
stability is a benefit; this file is an artefact.
"""
import json, os, sys, datetime, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw.json")
PREV = os.path.join(ROOT, "data", "previous.json")
SITE = os.path.join(ROOT, "site")
FEED = os.path.join(SITE, "data", "changes.json")
SCHEMA_VERSION = "1.0"


def key(row):
    # Some rows carry no category. Coerce to strings so the tuple always sorts:
    # a None in a sort key fails only on the days the data changes, which is the
    # worst possible day for it to fail.
    return (str(row.get("member_state") or ""),
            str(row.get("category_id") or ""),
            str(row.get("rate_type") or ""))


def index(rows):
    out = {}
    for r in rows:
        out[key(r)] = r
    return out


def codes_of(row):
    return {c["code"] for c in row.get("codes", [])}


def main():
    if not os.path.exists(RAW):
        print("no data to compare")
        return 1
    cur = json.load(open(RAW))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    if not os.path.exists(PREV):
        feed = {"schema_version": SCHEMA_VERSION, "generated_at": now,
                "baseline": True,
                "note": ("First publication. There is nothing to diff against yet, so this is the "
                         "baseline every later change is measured from."),
                "situation_on": cur["situation_on"], "row_count": cur["row_count"],
                "changes": []}
    else:
        prev = json.load(open(PREV))
        a, b = index(prev["rows"]), index(cur["rows"])
        changes = []
        for k in sorted(set(b) - set(a)):
            r = b[k]
            changes.append({"type": "rate_added", "member_state": r["member_state"],
                            "category_id": r["category_id"], "rate_type": r["rate_type"],
                            "new_value": r["rate_value"],
                            "affected_codes": sorted(codes_of(r))[:50],
                            "affected_code_count": len(codes_of(r))})
        for k in sorted(set(a) - set(b)):
            r = a[k]
            changes.append({"type": "rate_removed", "member_state": r["member_state"],
                            "category_id": r["category_id"], "rate_type": r["rate_type"],
                            "old_value": r["rate_value"],
                            "affected_codes": sorted(codes_of(r))[:50],
                            "affected_code_count": len(codes_of(r))})
        for k in sorted(set(a) & set(b)):
            ra, rb = a[k], b[k]
            if ra["rate_value"] != rb["rate_value"]:
                changes.append({"type": "rate_changed", "member_state": rb["member_state"],
                                "category_id": rb["category_id"], "rate_type": rb["rate_type"],
                                "old_value": ra["rate_value"], "new_value": rb["rate_value"],
                                "affected_codes": sorted(codes_of(rb))[:50],
                                "affected_code_count": len(codes_of(rb))})
                continue
            added, removed = codes_of(rb) - codes_of(ra), codes_of(ra) - codes_of(rb)
            if added or removed:
                changes.append({"type": "codes_reclassified", "member_state": rb["member_state"],
                                "category_id": rb["category_id"], "rate_value": rb["rate_value"],
                                "codes_added": sorted(added)[:50], "codes_removed": sorted(removed)[:50],
                                "codes_added_count": len(added), "codes_removed_count": len(removed)})
        feed = {"schema_version": SCHEMA_VERSION, "generated_at": now, "baseline": False,
                "situation_on": cur["situation_on"],
                "compared_with": prev["situation_on"],
                "row_count": cur["row_count"],
                "change_count": len(changes),
                "affects": sorted({c["member_state"] for c in changes}),
                "changes": changes}

    os.makedirs(os.path.dirname(FEED), exist_ok=True)
    json.dump(feed, open(FEED, "w"), ensure_ascii=False, indent=1)
    json.dump(cur, open(PREV, "w"), ensure_ascii=False, indent=1)
    print("change feed: %s, %d change(s)" %
          ("baseline" if feed.get("baseline") else feed["situation_on"], len(feed["changes"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
