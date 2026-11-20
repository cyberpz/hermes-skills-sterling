# Sterling BP queues / priority — tuning (IBM-doc verified)

## Queue model

- BP `Priority` 1–10 (1 = highest) maps the BP onto internal queue Q1–Q9/Q10. Default = 7: if nobody ever touched priorities, almost all traffic sits on Q7.
- Priority does NOT allocate threads: threads are per-queue. High priority on a queue with no threads changes nothing.
- BP priority change: applies to NEW instances only; live instances stay in the old queue.
- Bulk priority change: ONLY via API `BusinessProcessService` (getBusinessProcess/setBusinessProcess) — no bulk in the UI.

## Per-queue properties (file `noapp.properties_<host>_<node>_ext`, then setupfiles + restart)

| Property | Default | Role |
|---|---|---|
| `AE_ExecuteCycle.#` | 10000 | BP processed per cycle on one thread (low = interactive responsive, high = batch throughput) |
| `AE_ExecuteCycleTime.#` | 0 (off) | max seconds per cycle, anti thread-hogging |
| `MinPoolSize.#` / `MaxPoolSize.#` | 1 / 2×CPU | threads dedicated to the queue; sum of Min ≤ MaxThreads (license) |
| `QueueDepth.#` | 10000 | queue depth cap — leave default |
| `product.maxGlobalWorkers` | 4×CPU | node global thread cap |

## Scheduling policy (System > Administration > Scheduling Policy)

- `BasicSchedulingPolicy` vs `FairShareSchedulingPolicy`. FairShare: `ResourceAllocation.#` (% per queue), `StealThreads.#` (default 1) + `AllowStealing.#` (default true) → idle queues lend threads to loaded queues (e.g. a batch queue by day lends threads to the transactional queue).

## Load-balancing best practices

1. Isolate long-running and external-wait BPs (SAP RFC, IO wait) from short queues: cause no.1 of head-of-line blocking.
2. Progressively empty the default queue (Q7).
3. Before/after baseline with QueueWatcher (depth, min/used/max per queue) — without measurement you cannot prove improvement.
4. Queue thread tuning = node restart: plan it in a night window.

## Analysis scripts

Build a read-only SQL analysis pack against the Sterling DB (SELECT-only guard, fail-safe classifier refusing any non-read statement) covering: WFD columns check (is PRIORITY exportable from DB, else export via API); runs/avg-duration/p95 per BP (short vs long vs batch); live instances, halted (450) and long-running >30min; IO/SAP waits per service (head-of-line risk); hourly volumes (nightly batch vs intra-day); dead BPs 30+ days old (deactivate, don't re-queue). Dump CSV per section for offline review.

## Work phases

A: analysis (scripts + QueueWatcher screenshots: how many queues have consumers and min/used/max threads — the DB does not see threads). B: proposed BP→queue matrix, approved by the manager BEFORE touching anything. C: bulk priority set via API with dry-run + thread tuning in a night window.

## Example queue schema (propose, approve, then apply)

Q1 critical interactive (AS2 receipt/MDN) · Q2 core transactional (ORDERS/DESADV/INVOIC) · Q3 notifications · Q4 external waits (SAP RFC) · Q5 nightly batch (03:00–06:30) · Q6 secondary batch/reprocessing · Q7 default to empty · Q8 reporting/statistics.
