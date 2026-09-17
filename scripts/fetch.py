#!/usr/bin/env python3
"""Fetch EU VAT rates keyed to CN/CPA commodity codes from the Commission's TEDB.

Source: DG TAXUD, Taxes in Europe Database, VatRetrievalService.
Licence: Commission Decision 2011/833/EU, CC BY 4.0. Reuse permitted with credit
and an indication of changes. This reshapes the data; it does not alter the rates.

The one thing that will waste your afternoon: the SOAPAction header is mandatory
and must match exactly. Without it the service returns 404 with an empty body,
which reads like a wrong URL rather than a wrong header.
"""
import json, os, re, sys, datetime, urllib.request, urllib.error

ENDPOINT = "https://ec.europa.eu/taxation_customs/tedb/ws/VatRetrievalService"
SOAP_ACTION = "urn:ec.europa.eu:taxud:tedb:services:v1:VatRetrievalService/RetrieveVatRates"
NS = "urn:ec.europa.eu:taxud:tedb:services:v1:IVatRetrievalService:types"
# Greece is EL in this service, not GR. Sending GR fails the whole request.
MEMBER_STATES = ["AT","BE","BG","CY","CZ","DE","DK","EE","EL","ES","FI","FR","HR",
                 "HU","IE","IT","LT","LU","LV","MT","NL","PL","PT","RO","SE","SI","SK"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def envelope(states, situation_on):
    iso = "".join("<urn:isoCode>%s</urn:isoCode>" % s for s in states)
    return ('<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:urn="%s"><soapenv:Header/><soapenv:Body>'
            '<urn:retrieveVatRatesReqMsg><urn:memberStates>%s</urn:memberStates>'
            '<urn:situationOn>%s</urn:situationOn>'
            '</urn:retrieveVatRatesReqMsg></soapenv:Body></soapenv:Envelope>'
            % (NS, iso, situation_on))


def call(states, situation_on, timeout=180):
    req = urllib.request.Request(
        ENDPOINT, data=envelope(states, situation_on).encode("utf-8"),
        headers={"Content-Type": "text/xml;charset=UTF-8", "SOAPAction": SOAP_ACTION})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def tag(block, name):
    m = re.search(r"<%s>(.*?)</%s>" % (name, name), block, re.S)
    return m.group(1).strip() if m else None


def parse(xml):
    """Turn the SOAP body into rows. One row per member state per rate per category."""
    rows = []
    for block in re.findall(r"<vatRateResults>(.*?)</vatRateResults>", xml, re.S):
        rate = re.search(r"<rate>(.*?)</rate>", block, re.S)
        rate_block = rate.group(1) if rate else ""
        cat = re.search(r"<category>(.*?)</category>", block, re.S)
        cat_block = cat.group(1) if cat else ""
        codes = []
        for kind in ("cnCodes", "cpaCodes"):
            section = re.search(r"<%s>(.*?)</%s>" % (kind, kind), block, re.S)
            if not section:
                continue
            for c in re.findall(r"<code>(.*?)</code>", section.group(1), re.S):
                v, d = tag(c, "value"), tag(c, "description")
                if v:
                    codes.append({"kind": "CN" if kind == "cnCodes" else "CPA",
                                  "code": v, "description": d})
        rows.append({
            "member_state": tag(block, "memberState"),
            "rate_class": tag(block, "type"),
            "rate_type": tag(rate_block, "type"),
            "rate_value": tag(rate_block, "value"),
            "situation_on": (tag(block, "situationOn") or "")[:10],
            "category_id": tag(cat_block, "identifier"),
            "category_description": tag(cat_block, "description"),
            "comment": tag(block, "comment"),
            "codes": codes,
        })
    return rows


def main():
    situation_on = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    try:
        xml = call(MEMBER_STATES, situation_on)
    except urllib.error.HTTPError as e:
        print("TEDB refused the request: HTTP %s. Check the SOAPAction header." % e.code)
        return 1
    except Exception as e:
        print("TEDB unreachable: %s" % e)
        return 1
    if "faultstring" in xml:
        print("TEDB fault: " + (re.search(r"<faultstring>([^<]*)", xml) or [""])[0])
        return 1
    rows = parse(xml)
    if not rows:
        print("TEDB returned no rows. Refusing to overwrite good data with nothing.")
        return 1
    out = {
        "source": "European Commission, DG TAXUD, Taxes in Europe Database (TEDB)",
        "source_url": ENDPOINT,
        "licence": "CC BY 4.0 (Commission Decision 2011/833/EU). Reshaped, not altered.",
        "attribution": "© European Union, source: DG TAXUD TEDB",
        "situation_on": situation_on,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "member_states": sorted({r["member_state"] for r in rows if r["member_state"]}),
        "row_count": len(rows),
        "rows": rows,
    }
    path = os.path.join(ROOT, "data", "raw.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
    codes = {c["code"] for r in rows for c in r["codes"]}
    print("%d rows, %d member states, %d distinct commodity codes -> data/raw.json"
          % (len(rows), len(out["member_states"]), len(codes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
