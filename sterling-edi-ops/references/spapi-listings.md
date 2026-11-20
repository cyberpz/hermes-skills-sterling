# Amazon SP-API listings integration — details

Context constraints that shaped this design: no TypeScript/JavaScript SDK allowed, IBM Sterling produces files and never calls REST directly, legacy Oracle DB on the ERP side.

## Documentation retrieval (procedure)

1. HTML-rendered developer-docs pages are sparse/empty: request the `.md` version of the URL (e.g. `https://developer-docs.amazon.com/sp-api/recipes/submit-a-listings-item.md`) and use the index `https://developer-docs.amazon.com/sp-api/llms.txt` to find the right pages.
2. The real data structure is NOT in the doc pages: it is in the OpenAPI models on GitHub — `https://raw.githubusercontent.com/amzn/selling-partner-api-models/main/models/<api>-model/<model>.json`. Caution: Listings models are Swagger 2.0 → schemas under the `definitions` key, not `components.schemas`.
3. Attribute schemas are dynamic per productType: `GET /definitions/2020-09-01/productTypes/{productType}?marketplaceIds=...` (Product Type Definitions API) returns the JSON Schema with required/optional attributes, types and enums. Starting point for every master-data→attributes mapping.

## Authentication (Listings Items = non-restricted data)

- `POST https://api.amazon.com/auth/o2/token` with `grant_type=refresh_token` + client_id + client_secret + LWA refresh_token (can reach 2048 bytes: mind field-length limits in Sterling). Bearer token valid 3600 s → cache with refresh ~50 min, not per call.
- Listings Items is not restricted data: no SigV4, no Restricted Data Token. Per-call headers: `x-amz-access-token`, `x-amz-date` (UTC `YYYYMMDDTHHMMSSZ`), `user-agent` (mandatory), `host`.
- EU endpoint: `sellingpartnerapi-eu.amazon.com`; marketplace IT = `APJ6JRA9NG5V4`. The LWA host (`api.amazon.com`) differs from the SP-API host: both go in the corporate firewall outbound allow-list.

## Data structure (recurring pitfalls)

- `attributes`: open object, key = attribute name, value = ALWAYS an array of objects, even for a single value.
- PUT = full item replacement; PATCH = partial update with JSON Patch RFC 6902 (`op`: add/replace/merge/delete, JSON Pointer paths like `/attributes/item_name/0/value`).
- `requirements`: `LISTING` (full) | `LISTING_OFFER_ONLY` (price/qty only) | `LISTING_PRODUCT_ONLY`.
- Test phase: always use `mode=VALIDATION_PREVIEW` in the query — validates without touching production.
- Response `ListingsItemSubmissionResponse`: `status` ACCEPTED (accepted, async processing) or INVALID with `issues[]` (code, message, severity, attributeNames). Issues are the only validation feedback: always log them into an error table.

## Canonical CSV (intermediate mapping format)

One row = one field of one element of one attribute (row-per-SKU cannot hold arrays):
`seller_id, sku, marketplace_ids, product_type, requirements, attr_name, attr_index, field_name, field_value, field_type`
- `attr_index` = position in the attribute's array (multi-value: several images → 0,1,2...).
- `field_name` = field inside the element object (`value`, `language_tag`, `type`, `media_location`, `amount`, ...).
- `field_type`: `string` (default) | `number` | `boolean` | `null` — Amazon wants real numbers and booleans, not strings.
- Empty `field_value` → field omitted from the JSON.

Converter pattern (stdlib Python 3): read the canonical CSV → one `{sku}.json` per item with `{method, path, query, body}` (body = ready PUT body) + `manifest.json` for the delivery step. Keep the converter pure (no network) so it is unit-testable; delivery (auth + HTTP + issues logging) is a separate step.

## Before proposing the operational plan

Clarify from the Amazon request: operation (full PUT vs PATCH vs offer-only), productType and marketplaces involved, existing SP-API app credentials (client id/secret + refresh token) or a new private app to register.
