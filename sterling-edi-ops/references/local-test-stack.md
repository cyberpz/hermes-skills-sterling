# Local test stack (Oracle Free + Tomcat in Docker) for a Sterling-side WAR

Generic recipe to test a Java webapp that reads a Sterling-like Oracle schema, fully local.

## Stack

- `oracle-free` container (`gvenzl/oracle-free:23-slim-faststart`, port 1521, `ORACLE_PASSWORD` env — NOT `ORACLE_PWD`; `APP_USER=<appuser>`). Init SQL in `test/oracle/` runs only on FIRST init (empty volume). Mounted init scripts run as sys in CDB$ROOT: they MUST start with `ALTER SESSION SET CONTAINER=FREEPDB1;` (exact name, the PDB is FREEPDB1). Manual re-run: `docker cp` + `sqlplus -s sys/<pw>@FREEPDB1 as sysdba`. The app user needs explicit `GRANT SELECT` on every seeded schema object (ORA-00942 also means missing grant, not just missing table).
- Tomcat container (`tomcat:9.0-jre11-temurin`): mounts the WAR at `webapps/<app>.war`, JNDI context at `conf/Catalina/localhost/<app>.xml` (Resource `jdbc/<NAME>` → `jdbc:oracle:thin:@//host.docker.internal:1521/FREEPDB1`, needs `--add-host=host.docker.internal:host-gateway`), `ojdbc11.jar` in `/usr/local/tomcat/lib`.
- Portable one-shot stack: `docker-compose.yml` (oracle+tomcat) with explicit healthcheck `test: ["CMD-SHELL","/opt/oracle/healthcheck.sh"]` — the image has NO built-in HEALTHCHECK so `depends_on: service_healthy` needs this explicit one.
- Bundle pattern for handover: a script that builds a self-contained tar.gz (war, compose with ./ paths, seed SQL, README with test users + `docker save/load` offline recipe). Verify fresh-init end-to-end before shipping.
- Build: plain `javac --release 11` + `javax.servlet-api-4.0.1.jar` from Maven Central (verify sha256). Redeploy = rebuild + `docker restart` the tomcat container.
- The servlet app logs to `/usr/local/tomcat/logs/localhost.<date>.log` inside the container, NOT `docker logs`.

## API test suite

Keep a stdlib-only runner (`urllib`, form-encoded POSTs) hitting every endpoint: auth 401s, per-user filters, summary counts, dynamic columns, detail filters, injection attempts (expect 400), logout (POST — an empty body degrading to GET/400 is a bug), static assets. Re-run after every backend change.

## ExtJS pitfalls (legacy frontends)

- A vendored slim `ext-all.js` build may lack `Date.prototype.format`, `Ext.data.Model.create`, `Ext.defined` — use plain helpers and `Ext.define` + `Ext.ClassManager.isCreated`. Symptom: app silently fails to build after login, error inside ext-all.js.
- Ext 4.2 Store dedupes records by model `idProperty` (default `id`). Rows sharing `id` → grid silently shows only 1 row. Fix: explicit model with `idProperty` set to a truly unique column. Any store fed by rows lacking a unique `id` needs an explicit model/idProperty.
- Filter-bar alignment: two `hbox` rows of FIXED-width fields, all fields the same width so columns line up at identical x between rows; DateField pickers + Enter-to-search. Nested `layout:'column'` with `columnWidth` fractions is NOT reliable — inner containers shrink-wrap and fields collapse. Verify widths numerically after any layout change, don't trust the config.

## UI verification loop (browser, no vision needed)

API suite green ≠ UI works — the grid bugs above were invisible to the API suite. After ANY frontend change: rebuild + restart container, then browser E2E via CDP/browser automation:
- Login through the Ext API (`Ext.ComponentQuery.query('window textfield')` → `setValue` → click the button by `.x-btn-inner` text) — raw DOM typing can hit hidden/stale inputs and login silently fails.
- Trigger actions through the component handler (`Ext.ComponentQuery.query('button[text=Search]').filter(b=>b.isVisible())[0].handler()`), not DOM clicks.
- Assert DATA, not pixels: visible grid `getStore().getCount()` must equal the API row count; compare against DB ground truth via `sqlplus` in the oracle container when in doubt.
- Assert LAYOUT numerically: `getBoundingClientRect()` x/y per field (equal x across rows = aligned) and `getWidth()` / `inputEl.getWidth()` (inputs ≥ ~70px or they clip).
- Viewport: `Emulation.setDeviceMetricsOverride` then RELOAD — layout only recomputes on load.
- Screenshot for the record, but never gate verification on seeing the image.
- Debugging a store that loads 0 rows: a load callback that never fires means the reader/model threw — replay the same URL via `Ext.Ajax.request` + `store.loadData(rows)` to isolate proxy vs reader; "c is not a constructor" = store without fields/model.

## Data/tooling pitfalls

- File writers with transcript masking can write literal `***` into files when content contains password-looking values. Verify on-disk bytes (count `b'***'`) and build such strings by concatenation.
- Seed test data with SYSDATE-relative dates (`SYSDATE-1+minutes/1440`), never fixed `TO_DATE` literals — UIs default to a recent date range and fixed old dates render empty grids that look like broken queries.
