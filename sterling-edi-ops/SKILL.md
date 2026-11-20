---
name: sterling-edi-ops
description: Use for Sterling B2B Integrator EDI operations: log triage, BP queue tuning, MXL maps, WAR extensions.
version: 1.0.0
author: Giuseppe Vitale
license: MIT
metadata:
  hermes:
    tags: [sterling-b2b, edi, oracle, logs]
    related_skills: [sterling-map-compile]
---

# Sterling B2B Integrator — operations (general)

Umbrella for day-to-day Sterling EDI work: log-archive triage, BP queue tuning, MXL maps, web WAR extensions on Sterling.

## Always-on constraints

- On corporate Sterling environments: keep develop/test local; present the plan and get explicit approval BEFORE any real deploy or Sterling config change — silence is never a go-ahead.
- If the Sterling DB is old Oracle (10g): no `JSON_OBJECT`, no `PIVOT` — the DB emits flat rows, JSON generation is a separate stdlib-Python step; month matrices via `SUM(CASE WHEN ...)` conditional aggregation. Driver `oracledb` (thick mode), never cx_Oracle. Chunk `IN` lists at 999 (Oracle 1000 limit).
- Extended rule script (Sterling extended rule language, verified against IBM docs): string functions available ONLY `concat left mid right len strstr index insert` — `trim`, `strreplace`, `upper`, `lower` DO NOT exist. `concat(target, source, num_char)` MODIFIES target in place (returns no value). `mid(s, start[, len])` and `strstr` are zero-based; strstr returns -1 when not found. Control syntax: `if cond then begin ... end else cond then begin ... end` (no `endif`, no `;` after the condition); `while cond do begin ... end`; `break;` exits the while. Variable declarations `String[60] vX;` / `Integer n;` at the top of the rule. Padding-space strip: while loop with `right(s,1)=" "` + `left(s, len-1)`.
- MXL/Map Editor extended rules: single-line strings beyond ~300 characters make compilation fail (mapper bug, verified on a PRICAT D96A map — 277 chars compile, ~300+ do not; rule of thumb: keep lines <250). Split long SQL into short chunks: `sql = sql + "..."`. Rules of GROUPS (e.g. ITEM_GROUP with `ob.Open("<pool>", sql)` queries) are NOT in `ExplicitRule` but in the group's `OnBegin`/`OnEnd` elements — a script that scans only ExplicitRule misses them. Every `ob.Open` requires its `ob.Close()` before the next Open, and `ob.getString` is case-sensitive on column names (Oracle returns uppercase).
- ibm.com/docs returns 403 to curl/web_extract/browser fetch (Akamai). Working path: `curl -sL "https://r.jina.ai/<full ibm docs url>"` — public doc URLs only.

## Web extension (WAR on Sterling)

- Mandatory webapp structure under `<install>/install/container/applications/<root>/`: `web.xml`, `TLD/` (must exist even if unused — copy a `.tld` from an existing extension), `classes/`, `lib/`. Deploy with `Deployer.sh` from `<install>/install/bin` — it redeploys ALL WARs on the node: warn before running on shared nodes.
- Sterling tag libs (`authenticate`, `validSession`, `RunBusinessProcess`) reuse Sterling's own users. JNDI datasource name is environment-specific (typically `jdbc/GICDB`): env-entry in web.xml + a `.properties` direct-JDBC fallback; verify the real name on the target before deploy.
- `<secure>true</secure>` cookie-config over plain http silently drops the session cookie on LAN-IP access (localhost is exempt → local tests pass, remote fails). Keep secure off unless serving https.
- Delegated frontend code written against an API contract WITHOUT a live backend produces systematic mismatches (camelCase vs snake_case, form-encoded `params:` vs JSON body, invented response keys). Always run an integration pass against the running backend; when mismatches are systematic, rewrite the file against the exact contract instead of patching.
- A green API suite does NOT prove the UI works — grid bugs (missing store model, `idProperty` dedupe) pass every API test while rendering nothing. After any frontend change run a browser E2E: assert visible-grid store counts against API/DB and measure field alignment/widths numerically; deliver a screenshot.
- Local test stack (Oracle Free + Tomcat in Docker) and ExtJS pitfalls: `references/local-test-stack.md`.

## Log triage ("what happened at HH:MM")

- Rotation naming `<log>.D<YYYYMMDD>.T<HHMMSS>` = file CREATED at that time; content runs FROM that timestamp to the next rotation. Always verify the real per-file range with `head -1`/`tail -1` before grepping a window — wrong-file greps produce false "no errors at that hour".
- Two timestamp formats: `[YYYY-MM-DD HH:MM:SS.mmm]` (noapp/system/EDIINT/ftpclient/Perimeter/tracking/visibility) and `MM-DD-YYYY HH:MM:SS:mmm` (cla2server/client). Build grep patterns per format.
- `ERROR`/`ERRORDTL` = signal; `ALL`/`DEBUG`/`FINE` = noise. The verdict lives in the `Caused by:` lines of ERRORDTL — always read them before concluding.
- Chronic-vs-sudden test is MANDATORY before any verdict: aggregate errors per hour over the whole file (`grep <pat> | sed -E 's/^\[([0-9-]+ [0-9]{2}):.*/\1/' | uniq -c`). Known chronic baselines: `references/log-triage.md`.
- Correlate a document's flow by grepping its `WFID:NNNN` across the channel logs (sap/ftpclient/cla2server/tracking). BP backlog: check flood vs stuck-consumer FIRST; `Interrupted_Man` leaves no log trace (DB `WORKFLOW_CONTEXT.BASIC_STATUS=450`). Status codes and root causes: `references/log-triage.md`.

## BP queues / priority tuning

- BP priority 1–10 → internal queue code Q1–Q9/Q10 (default 7); threads are per-queue, NOT per-priority; bulk priority changes ONLY via API `BusinessProcessService`. Tuning properties, FairShare scheduling policy, example queue schema, analysis-script approach: `references/queue-tuning.md`.

## MXL maps (Sterling Map Editor)

- Exported xlate maps are XML (namespace `stercomm.com/SI/Map`): analyze and modify them as text (raw surgery, NEVER re-serialize with ElementTree), then re-import into the Map Editor to validate. Mapping links = `<Link>` elements (source ID inside the output node); there are NO MapRef/Translation elements. Structure, dump via `scripts/dump_map.py`, edit recipe and pitfalls: `references/sterling-mxl-maps.md`.
- Binary `.map` export (GENTRAN template source, `file` says "data"): embedded scripts stay readable in cp1252 — locate hardcoded literals with `grep -a -b <pattern>` (gives the byte offset) and dump context with python. Every script statement is preceded by a length byte: patch with an in-place SAME-LENGTH substitution (pad with spaces around `=`) so the prefix and offsets stay valid; verify identical file size, confined diff range, target-string count 0→1. After the patch: import + compile in the Map Editor in a test environment. Hardcoded literals (VAT, entity addresses) are often copied from the twin country's map: grep the literal before hunting the logical mapping.
- In the Sterling DB maps live as zipped BLOBs in `DATA_TABLE` (metadata in `MAP`/`MAP_VERSIONS`/`DATA_HEADERS`); headless compilation `mapper.exe -c` (also under Wine): see skill `sterling-map-compile` + `references/sterling-mxl-maps.md`.
