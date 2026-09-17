# EU VAT rates by commodity code

Which VAT rate applies to **this** product in **that** country, keyed to the same CN and
CPA commodity codes your customs paperwork already uses.

**2,667 commodity codes · 27 member states · 1,120 rate rows · rebuilt daily**

```bash
# every rate for one commodity code, across the EU
curl https://humora2504.github.io/eu-vat-by-commodity-code/data/by-code/4901.json

# everything one country charges
curl https://humora2504.github.io/eu-vat-by-commodity-code/data/by-country/DE.json

# what changed since the last build
curl https://humora2504.github.io/eu-vat-by-commodity-code/data/changes.json
```

## Why this exists

Published VAT tables give you a country's standard rate and its reduced rates. They do not
tell you **which goods** each reduced rate covers, and that is the part that costs money.
Two countries can both have a 10% reduced rate that applies to entirely different things.
Undercharge VAT and you cannot recover it from the customer: the shortfall comes out of your
margin, with interest.

The European Commission publishes this mapping in its Taxes in Europe Database. It is not
published anywhere as open, machine-readable data. Now it is.

## Shape

```json
{
  "code": "4901 99 00",
  "entries": [
    { "member_state": "FR", "country": "France", "rate_value": "2.1",
      "rate_class": "REDUCED", "category_description": "Newspapers",
      "code_description": "Other",
      "comment": "Article 298 septies of the general tax code" }
  ]
}
```

The `comment` is the member state's own legal note, verbatim, not a summary.

## The change feed

`data/changes.json` lists every rate added, removed or changed since the last build, and
every commodity code reclassified, with the count of codes affected:

```json
{ "type": "rate_changed", "member_state": "DE", "old_value": "7.0",
  "new_value": "8.0", "affected_code_count": 84 }
```

That is the part worth watching. A rate moving is easy to notice. Eighty-four commodity
codes quietly moving between categories is not.

## Licence, stated plainly

The data is the European Commission's, licensed
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) under Commission Decision
2011/833/EU. **You may already use it commercially, for free, today.** We reshaped it into
JSON and pages and added nothing of our own.

Attribution to use: `© European Union, source: DG TAXUD TEDB`

The scripts here are MIT.

## What this is not

Not tax advice. Not a substitute for your own verification. Rates change; the situation date
is in every file. If a filing depends on it, check with your tax authority.

## Rebuilding it yourself

```bash
python3 scripts/fetch.py        # pull from TEDB
python3 scripts/build.py        # JSON + pages
python3 scripts/changefeed.py   # diff against the last build
python3 scripts/test.py         # 12 assertions
```

One thing that will cost you an afternoon if you try this yourself: TEDB's SOAP endpoint
requires the `SOAPAction` header set to exactly
`urn:ec.europa.eu:taxud:tedb:services:v1:VatRetrievalService/RetrieveVatRates`. Without it
you get a bare `404` with an empty body, which reads like a wrong URL rather than a wrong
header. Also, Greece is `EL`, not `GR`.

## Paid

Nothing here is paywalled and nothing will be. If you want a change feed filtered to only
the commodity codes you actually sell, that is
[a paid plan](https://humora2504.github.io/eu-vat-by-commodity-code/commercial.html).
