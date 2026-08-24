# Alpha Vantage — APIM Onboarding

Artifacts:

| File | Purpose |
|---|---|
| `alphavantage-openapi.yaml` | OpenAPI 3.0.1 spec, 116 operations across 10 tags. Validates against the 3.0.1 schema. |
| `apim-policy.xml` | API-scope policy. Path→function rewrite, key injection, quota, cache, error normalisation. |

## The one design decision that matters

Alpha Vantage serves everything from a single backend route:

```
GET https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=...
```

OpenAPI cannot express 116 operations on one path + method. Two ways out:

**A. One operation, `function` as an enum.** Faithful to the vendor, and useless in
APIM — you get one operation, so no per-operation products, policies, quotas, or
analytics, and the developer portal shows a single opaque call with 40 optional
parameters that are valid in mutually exclusive combinations.

**B. Promote each `function` to its own path** (`/TIME_SERIES_DAILY`, `/GLOBAL_QUOTE`, …)
and rewrite back to `/query` at the gateway. This is what the spec does.

The cost of B is 116 operations to keep in sync with the vendor. That cost is paid by
the generator script rather than by hand, and the path segment is the literal vendor
`function` value, so troubleshooting against the vendor docs stays a direct lookup.

Because the path segment *is* the function name, one API-level policy covers all 116
operations — there is no per-operation configuration to maintain:

```xml
<set-variable name="avFunction"
              value="@(context.Request.OriginalUrl.Path.TrimEnd('/').Split('/').Last())" />
<rewrite-uri template="/query" copy-unmatched-params="true" />
<set-query-parameter name="function" exists-action="override">
  <value>@((string)context.Variables["avFunction"])</value>
</set-query-parameter>
```

If your API governance standard mandates kebab-case REST paths, change the paths in the
generator and swap the variable for an operation-ID lookup table. Everything else holds.

## Import

```bash
RG=your-rg
APIM=your-apim-instance

# 1. Vendor key as a secret named value (Key Vault reference preferred)
az apim nv create -g $RG --service-name $APIM \
  --named-value-id alphavantage-apikey \
  --display-name alphavantage-apikey \
  --secret true --value "<YOUR_ALPHA_VANTAGE_KEY>"

# 2. Import the spec
az apim api import -g $RG --service-name $APIM \
  --api-id alphavantage \
  --path alphavantage/v1 \
  --specification-format OpenApi \
  --specification-path ./alphavantage-openapi.yaml \
  --service-url https://www.alphavantage.co \
  --protocols https \
  --subscription-required true

# 3. Apply the policy at API scope
az apim api policy create -g $RG --service-name $APIM \
  --api-id alphavantage \
  --policy-format xml \
  --value "$(cat apim-policy.xml)"
```

Smoke test:

```bash
curl -s "https://$APIM.azure-api.net/alphavantage/v1/GLOBAL_QUOTE?symbol=IBM" \
     -H "Ocp-Apim-Subscription-Key: $SUB_KEY"
```

## Three things that will bite you if skipped

**1. The vendor returns HTTP 200 for failures.** Rate limiting, missing entitlement, and
bad parameters all come back as `200 OK` with an `Error Message`, `Note`, or `Information`
field in the body. Downstream retry logic and circuit breakers see a healthy response and
do the wrong thing — a throttled client will hammer the endpoint and burn the daily quota
in minutes. The outbound policy parses the body and re-maps onto 400 / 403 / 429. Verify
this works before you publish; it is the highest-value part of the policy.

**2. Quota is per-account, not per-consumer.** Every consumer draws on one upstream key.
The free tier is 25 calls/day; paid tiers are priced per requests-per-minute. Set
`rate-limit-by-key` and `quota-by-key` below your contracted tier so the gateway rejects
overage instead of the vendor doing it unpredictably across all your consumers. The
caching block matters here too — daily and monthly series are effectively static within a
session, and caching them is the difference between a 75/min plan working and not.

**3. Premium operations fail confusingly on a free key.** Roughly 20 operations
(`TIME_SERIES_INTRADAY`, `TIME_SERIES_DAILY_ADJUSTED`, all `INDEX_DATA`, `REALTIME_*`,
`FX_INTRADAY`, `CRYPTO_INTRADAY`, `VWAP`, `MACD`) require a paid upstream plan and are
flagged in the spec descriptions. Put them in a separate APIM product so entitlement is
enforced at the gateway rather than surfacing as an opaque vendor message halfway through
someone's integration.

## Compliance note

Realtime and 15-minute delayed US market data is regulated by the exchanges, FINRA, and
the SEC, and Alpha Vantage's terms distinguish personal from commercial use. Onboarding
to a shared internal gateway is a redistribution question, not just a technical one — get
the licence scope confirmed before opening `entitlement=realtime` operations to a wide
internal audience, and consider gating those operations behind a named product with an
approval workflow.

## Regenerating

`generate_spec.py` holds the operation tables. To add or change an endpoint, edit the
relevant table and re-run — the response wiring, error responses, security scheme, and
shared parameters are applied uniformly, so hand-edits to the YAML will be lost. Validate
after any change:

```bash
python3 -m openapi_spec_validator alphavantage-openapi.yaml
```

## Known gaps

The vendor documentation page is long and a few newer endpoints are stubbed with base
parameters only, pending a pass against the live docs:

- `REALTIME_OPTIONS` / `HISTORICAL_OPTIONS` — `date`, `require_greeks`, `contract` not modelled
- `NEWS_SENTIMENT` — `tickers`, `topics`, `time_from`, `time_to`, `sort`, `limit` not modelled
- `EARNINGS_CALL_TRANSCRIPT` — `quarter` not modelled
- `LISTING_STATUS` / `EARNINGS_CALENDAR` — `date`, `state`, `horizon` not modelled
- Analytics (fixed/sliding window), congress trades, institutional holdings, politician
  metadata, company logo, and gold/silver spot are not yet included

Unmodelled query parameters still reach the backend — `copy-unmatched-params="true"`
forwards them — so these operations work; they are just under-documented in the portal.
