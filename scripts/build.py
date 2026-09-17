#!/usr/bin/env python3
"""Turn the raw TEDB pull into the published dataset and the indexable pages.

Two audiences. A machine wants data/by-code/4901.json. A person searching
"VAT rate for books in Germany" wants a page that answers in the first sentence.
"""
import json, os, re, html, datetime, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw.json")
OUT = os.path.join(ROOT, "docs")
BASE = "https://humora2504.github.io/eu-vat-by-commodity-code/"

COUNTRY = {"AT":"Austria","BE":"Belgium","BG":"Bulgaria","CY":"Cyprus","CZ":"Czechia",
 "DE":"Germany","DK":"Denmark","EE":"Estonia","EL":"Greece","ES":"Spain","FI":"Finland",
 "FR":"France","HR":"Croatia","HU":"Hungary","IE":"Ireland","IT":"Italy","LT":"Lithuania",
 "LU":"Luxembourg","LV":"Latvia","MT":"Malta","NL":"Netherlands","PL":"Poland",
 "PT":"Portugal","RO":"Romania","SE":"Sweden","SI":"Slovenia","SK":"Slovakia"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:80]


def build():
    raw = json.load(open(RAW))
    rows = raw["rows"]

    by_code = collections.defaultdict(list)
    by_country = collections.defaultdict(list)
    for r in rows:
        by_country[r["member_state"]].append(r)
        for c in r["codes"]:
            by_code[c["code"]].append({
                "member_state": r["member_state"], "country": COUNTRY.get(r["member_state"]),
                "rate_class": r["rate_class"], "rate_type": r["rate_type"],
                "rate_value": r["rate_value"], "category_id": r["category_id"],
                "category_description": r["category_description"],
                "code_kind": c["kind"], "code_description": c["description"],
                "comment": r["comment"], "situation_on": r["situation_on"]})

    meta = {k: raw[k] for k in ("source", "source_url", "licence", "attribution",
                                "situation_on", "fetched_at")}
    for d in ("data/by-code", "data/by-country", "code", "country"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    for code, entries in by_code.items():
        json.dump({**meta, "code": code, "entries": sorted(entries, key=lambda e: e["member_state"])},
                  open(os.path.join(OUT, "data/by-code", slug(code) + ".json"), "w"),
                  ensure_ascii=False, indent=1)
    for cc, entries in by_country.items():
        json.dump({**meta, "member_state": cc, "country": COUNTRY.get(cc), "rates": entries},
                  open(os.path.join(OUT, "data/by-country", cc + ".json"), "w"),
                  ensure_ascii=False, indent=1)
    json.dump({**meta, "row_count": len(rows), "rows": rows},
              open(os.path.join(OUT, "data/all.json"), "w"), ensure_ascii=False, indent=1)
    json.dump({**meta, "codes": sorted(by_code.keys()),
               "countries": {k: COUNTRY.get(k) for k in sorted(by_country)}},
              open(os.path.join(OUT, "data/index.json"), "w"), ensure_ascii=False, indent=1)

    pages = write_pages(by_code, by_country, meta)
    return len(by_code), len(by_country), pages


HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<link rel="stylesheet" href="{root}style.css">
<script type="application/ld+json">{ld}</script>
</head><body>
<header><div class="wrap"><a class="logo" href="{root}">EU VAT by commodity code</a>
<nav><a href="{root}data/">Data</a> <a href="{root}licence.html">Licence</a></nav></div></header>
<main class="wrap">
"""
FOOT = """
</main>
<footer><div class="wrap">
<p>&copy; European Union, source: European Commission, DG TAXUD, Taxes in Europe Database. Licensed
<a href="https://creativecommons.org/licenses/by/4.0/" rel="nofollow">CC BY 4.0</a> under Commission
Decision 2011/833/EU. Reshaped into JSON and pages; the rates themselves are unaltered.
Situation on {situation}, fetched {fetched}.</p>
<p class="small">This is reference data, not tax advice. Verify against your own tax authority before
relying on it for a filing. <a href="{root}commercial.html">Commercial use</a></p>
</div></footer></body></html>
"""


def rate_line(e):
    v = e["rate_value"]
    return "%s%%" % (v.rstrip("0").rstrip(".") if v and "." in v else v)


def write_pages(by_code, by_country, meta):
    n = 0
    for code, entries in by_code.items():
        desc = next((e["code_description"] for e in entries if e["code_description"]), "")
        title = "VAT rate for commodity code %s in the EU%s" % (code, (" — " + desc) if desc else "")
        rates = sorted(entries, key=lambda e: e["member_state"])
        rows = "\n".join(
            "<tr><td>%s</td><td><b>%s</b></td><td>%s</td><td>%s</td></tr>" % (
                html.escape(e["country"] or e["member_state"]), rate_line(e),
                html.escape((e["rate_class"] or "").replace("_", " ").title()),
                html.escape((e["category_description"] or "")[:90]))
            for e in rates)
        # Sort numerically. Sorting "13" and "5" as text says "from 13% to 5%",
        # which is visibly wrong and would discredit the whole dataset.
        def as_number(e):
            try:
                return float(e["rate_value"])
            except (TypeError, ValueError):
                return float("inf")
        numeric = sorted({as_number(e) for e in rates if as_number(e) != float("inf")})
        vals = [("%g%%" % v) for v in numeric]
        lead = ("Commodity code <b>%s</b>%s carries %s across the %d EU member states that report a "
                "rate for it. The full table is below, and the same data is available as "
                "<a href=\"%sdata/by-code/%s.json\">JSON</a>." % (
                 html.escape(code), (" (" + html.escape(desc) + ")") if desc else "",
                 ("a single rate of " + vals[0]) if len(vals) == 1
                 else ("rates from %s to %s" % (vals[0], vals[-1])) if vals
                 else "no numeric rate",
                 len({e["member_state"] for e in rates}), "../", slug(code)))
        ld = json.dumps({"@context":"https://schema.org","@type":"Dataset","name":title,
                         "description":"VAT rates by EU member state for commodity code " + code,
                         "license":"https://creativecommons.org/licenses/by/4.0/",
                         "creator":{"@type":"Organization","name":"European Commission, DG TAXUD"},
                         "url":BASE + "code/" + slug(code) + ".html"}, ensure_ascii=False)
        body = ("<h1>%s</h1>\n<p class=\"lede\">%s</p>\n"
                "<table><tr><th>Country</th><th>Rate</th><th>Class</th><th>Category</th></tr>%s</table>\n"
                % (html.escape(title), lead, rows))
        comments = [(e["country"], e["comment"]) for e in rates if e["comment"]]
        if comments:
            body += ("<h2>What the member states say</h2>\n<dl>" + "".join(
                "<dt>%s</dt><dd>%s</dd>" % (html.escape(c or ""), html.escape(t[:400]))
                for c, t in comments[:8]) + "</dl>\n")
        html_out = (HEAD.format(title=html.escape(title), desc=html.escape(
                        "VAT rates for commodity code %s across the EU, from the Commission's own database." % code),
                        canon=BASE + "code/" + slug(code) + ".html", root="../", ld=ld)
                    + body + FOOT.format(situation=meta["situation_on"],
                                         fetched=meta["fetched_at"][:10], root="../"))
        open(os.path.join(OUT, "code", slug(code) + ".html"), "w").write(html_out)
        n += 1
    return n


if __name__ == "__main__":
    codes, countries, pages = build()
    print("%d commodity codes, %d countries, %d pages" % (codes, countries, pages))
