# ODK Central tuning (ModSecurity + OWASP CRS)

This note documents the CRS tuning required to run ODK Central behind
ModSecurity (v3) + OWASP CRS without breaking core functionality.

The intent is to keep exclusions:

- as narrow as possible (endpoint-scoped)
- transparent (documented with rule IDs and examples)
- easy to override locally via bind mounts

## Why `/client-config.json` needs an exclusion

Central’s nginx entrypoint generates `/usr/share/nginx/html/client-config.json`
from `files/nginx/client-config.json.template`, and the frontend must fetch it
on page load.

OWASP CRS rule `930130` (“Restricted File Access Attempt”) can match
`config.json` in the URI path and block it, which cascades into
`949110` (inbound anomaly score threshold) and breaks the UI with a 403.

Mitigation:

- add a scoped exclusion for `/client-config.json` removing `930130`

See `crs_custom/10-odk-exclusions.conf` in the Central repo.

## Why OData `.svc/*` endpoints need exclusions

Central exposes OData-style endpoints (for example `*.svc/Submissions`) which
use query parameter names like `$filter`, `$orderby`, `$top`, `$skip`, etc.

CRS rule `942290` (SQLi detection) can false-positive on these *parameter
names* (e.g. `$filter`), resulting in a block.

Some requests can also trigger protocol enforcement `920100` depending on how
the request line is parsed/normalized with long, encoded query strings.

Mitigation:

- disable `942290` and `920100` only for:
  - `GET` requests
  - `.svc/(Submissions|Entities)` endpoints
  - requests that present Central session cookies (`__Host-session` or `__csrf`)

Rationale for cookie guard:

- It does not prove authentication, but it reduces exposure by avoiding blanket
  exclusions for unauthenticated traffic.
- Definitive auth is enforced by the upstream Central service anyway.

See `crs_custom/20-odk-odata-exclusions.conf` in the Central repo.

## Allowing Central API methods (`PUT`, `PATCH`, `DELETE`)

Central’s JSON API under `/v1/` uses standard REST methods including `PUT`,
`PATCH`, and `DELETE`.

CRS rule `911100` (“Method is not allowed by policy”) enforces a conservative
default allow-list (`GET HEAD POST OPTIONS`) and will block legitimate Central
API requests, which then cascades into `949110` (anomaly score threshold).

Mitigation:

- disable `911100` only for requests with a path prefix of `/v1/`
  and only when the request includes Central session-related cookies
  (`__Host-session` or `__csrf`).

See `crs_custom/30-odk-api-methods.conf` in the Central repo.

## PCRE limit tuning (`MSC_PCRE_LIMITS_EXCEEDED`)

Central OData queries can be long and heavily encoded. Under CRS, some requests
can exceed ModSecurity’s default PCRE match limits, raising
`TX:MSC_PCRE_LIMITS_EXCEEDED` and resulting in a block.

Mitigation:

- increase `SecPcreMatchLimit` and `SecPcreMatchLimitRecursion` to accommodate
  long but legitimate OData query strings.

This is currently applied in `files/nginx/vg-modsecurity-odk.conf` in the
Central repo.

## Load order: custom before CRS

Exclusions like `ctl:ruleRemoveById=...` must be evaluated before the
corresponding CRS rules run. For that reason, the ModSecurity config should
`Include /etc/modsecurity/custom/*.conf` before including the CRS setup and
rules.

## Validation tips

- Check nginx access logs: `./logs/nginx/access.log`
- Check ModSecurity audit logs: `./logs/modsecurity/audit.log`
- For a single failing request, use the `unique_id` from nginx error log to
  find the matching transaction in the audit log and identify the rule IDs.
