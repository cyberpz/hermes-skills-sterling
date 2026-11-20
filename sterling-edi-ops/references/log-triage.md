# Sterling B2B log-archive triage — full playbook

Goal: distinguish sudden incidents from chronic noise and deliver a verdict (time | log | error | cause + conclusion), not an error dump.

## Structure and formats

- Rotation naming: `<log>.D<YYYYMMDD>.T<HHMMSS>` = file **created** at that hour; content starts FROM that timestamp until the next rotation. Before grepping a window, verify each file's real range with `head -1`/`tail -1` — grepping the "wrong" file looks like "no errors at that hour".
- Two timestamp formats: `[YYYY-MM-DD HH:MM:SS.mmm] LEVEL ...` (noapp, system, EDIINT, sap, ftpclient, Perimeter, tracking, visibility, wf, tx) and `MM-DD-YYYY HH:MM:SS:mmm` (cla2server, cla2client). Build the grep pattern per format.
- Levels: `ALL`, `DEBUG`, `FINE` = noise; `ERROR`, `ERRORDTL` = signal. Standard filter: `grep -E "^\[YYYY-MM-DD HH:[0-5]" <file> | grep -vE "\] ALL |\] DEBUG|\] FINE"`.
- ERRORDTL contains the full stack: the verdict is in the `Caused by:` lines — always read them before concluding.

## Procedure

1. Unzip into a scratch dir; inventory the files.
2. Real time range of each file (head/tail) → map which file covers the requested window.
3. Grep the window across all relevant files, filter noise levels → error clusters.
4. **Chronic-vs-sudden test (key step)**: aggregate errors per hour over the whole file — `grep <pattern> | sed -E 's/^\[([0-9-]+ [0-9]{2}):.*/\1/' | uniq -c`. Present for hours/days = background noise, say so; new in the window = incident.
5. Dig `Caused by` in ERRORDTL for the root cause.
6. Correlate by WFID: the same `WFID:NNNN` appears across channel logs — grep the WFID across all logs to rebuild the flow of the affected document.
7. Verdict table (time | log | error | cause) + conclusion: if the user has a concrete symptom, ask for the affected document/partner and trace back to the WFID.

## Known chronic noise (baseline, not incidents)

- `ftpclient`/`Perimeter`: `CloseCode.READ_FAILURE` on data connections (peer closes data connection) — dozens/hour in normal regime.
- `noapp`: `There is no command limiting policy defined`, `commandLimitingPolicy is null`, `fireCommAuthorizationEvent null principal`, XML `no grammar found` / `Document root element ... must match DOCTYPE` (DTD validation disabled).
- `tracking`: recurring `StatsArchiveService: Failed to archive stats`.
- `visibility`/`ftp`: `createDirectory not accepted` errors at regular intervals (misconfigured probe).

## BP backlog (Active exploding, Interrupted_Man)

- If BP Active jumps from tens to thousands: check FIRST whether it is inbound flood or blocked consumption. Flood = anomalous volumes (EDIINT processData count, FTP logins, cla2server cmd rate per hour). Flat volumes → blocked consumption (slow external resources: DB/RFC).
- `Interrupted_Man` leaves NO trace in log files: in the Sterling DB it is `WORKFLOW_CONTEXT.BASIC_STATUS = 450` (Interrupted Manual Intervention Required). Zero "interrupt" greps in logs = manual interruptions via UI/API.
- BP state from the DB (verify the exact view/table names in your environment — some deployments expose these as views over the internal schema): `WORKFLOW_CONTEXT` (WORKFLOW_ID, WFD_ID, WFD_VERSION, STEP_ID, BASIC_STATUS, SERVICE_NAME, START_TIME, ADV_STATUS=error, DOC_ID), `WFD` (WFD_ID+WFD_VERSION→NAME = BP name), `ARCHIVE_INFO` (WF_ID, ARCHIVE_FLAG=-1 = not archived), `WORKFLOW_LINKAGE` (ROOT_WF_ID, C_WF_ID). BASIC_STATUS: 0 Active, 1 Error, 3 Waiting, 10 WaitIO, 100 Halted, 200 SysErr, 300 ConfigErr, 400 IntAuto, 450 Interrupted_Man, 900 Terminated. Real BP state = BASIC_STATUS of MAX(STEP_ID).
- Nightly delivery-note batch: typical window 03:00-06:30 with a ~05h peak. Count unique documents per hour with `grep -oE '<DOC_PREFIX>_[0-9]+' | sort -u` per hour.
- HANA under pressure: `SAP DBTech JDBC: [2048] column store error ... [9] Memory allocation failed` (in tx.log, NOT system.log!) = slow/hung HANA queries → stalling BPs. Correlate with BP peak.
- `INITIATING_CONTEXT_WFC_ERROR_*` + `StreamCorruptedException: unexpected reset` in system.log = corrupted serialized BP contexts, consistent with aftermath of mass interruptions.
- Recurring constraint violations in translation SQL blocks (ORA-01400 NOT NULL, ORA-00001 unique, HANA [301] unique): chronic data quality issues, NOT a backlog cause — do not chase them during an incident.

## Known root causes

- SAP JCo integration: `JCO_ERROR_SYSTEM_FAILURE` with a message like "Fill out all required entry fields" (raised by the SAP system) = **functional error on the SAP side**, RFC payload with missing mandatory fields — NOT a network/connectivity problem. A workflow failing at regular intervals (e.g. every 10 min) indicates a scheduled BP with incomplete data.
- `XSLT Service failed ... Premature end of file` = document fed to translation empty/truncated upstream.
- `sftpclient` `No such file` = file missing on the partner server (remote side).

## Pitfalls

- Never conclude "no errors" from an empty grep before checking timestamp format and file range: two different formats and counterintuitive rotation naming produce false negatives.
- Never present chronic noise as an incident: per-hour counts over the whole file are mandatory before the verdict.
- cla2server is only a shell-command AUDIT log (rm/mv of EDI files): useful to trace file lifecycle, contains no application errors.
