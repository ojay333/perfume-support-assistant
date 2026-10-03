# Verification record

This file separates recorded earlier evidence from checks of this delivery package. A written command or copied test file is not proof of execution. No credentials, local account data, or private customer data belong in this record.

## Recorded evidence before this package's verification

| Date | Check | Recorded result | Scope and limit |
|---|---|---|---|
| 2026-09-30 | Nine local test files | Passed, including 15 `test_rag_client.py` cases | Mocked provider tests and local policy/index checks; not the twenty-case evaluation |
| 2026-09-30 | Direct deadline question through FastAPI TestClient + live Gemini | 3 days; `p1-c1`, page 1; 1.95 s | Answer text and source were manually reviewed |
| 2026-09-30 | Reworded follow-up requirements question through TestClient + live Gemini | Order ID, photo, retain packaging; `p1-c1`, page 1; 2.14 s | One observed run, not a paraphrase benchmark |
| 2026-09-30 | Jeddah delivery question through TestClient + live Gemini | `insufficient_evidence`, `sources: []`; 2.15 s | One out-of-document example |
| 2026-09-30 | Isolated in-memory source with a 3-day policy and injected 99-day/refund instructions | Answer retained the 3-day policy; 6.32 s | Original PDF, chunks and index were not changed; not comprehensive injection testing |
| 2026-09-30 | n8n 2.41.3 CLI execution against local FastAPI + live Gemini | Three nodes succeeded; HTTP 200, 3 days, `p1-c1` / page 1; about 2.85 s | One local assisted execution |
| 2026-09-30 | Separate n8n CLI fixture with whitespace input | HTTP 422, «النص مطلوب», workflow execution `error` | Expected rejection; no Gemini call for the invalid input |
| 2026-09-30 | Guided n8n editor demo after local owner-account setup | Supported answer with source shown; insufficient-evidence result and blank-input message reported | The editor report did not independently show a numeric 422; that code was verified in the separate CLI check above |
| 2026-10-01 | Guided `/health` and `/ask` check in Swagger | `ok`; answer and source said 3 days from receipt, `p1-c1` / page 1 | Existing local service; not a clean restart or fresh installation |

The four live RAG checks on 30 September used two provider calls each: eight calls in that set. The n8n CLI success check used two additional calls. Further guided user checks are recorded separately; no total provider-call count is inferred for them. Timings are observations, not latency guarantees.

The nine recorded test files were `test_rag_client.py`, `test_api.py`, `test_retrieval.py`, `test_policy_reader.py`, `test_llm_client.py`, `test_draft_schema.py`, `test_followup.py`, `test_followup_workflow.py`, and `test_ticket_client.py`. Earlier GitHub/Gate exercises were not part of that run.

## Delivery-package checks — 2026-10-03

The following outcomes were observed on this separately assembled package. Execution was assisted; these results do not establish an independent skills Gate.

| Check | Status | Evidence to record |
|---|---|---|
| Package contents and secret exclusion | `passed` | Explicit export allowlist; staged-file scan found no known key patterns or personal absolute paths. Runtime, `.env`, CV and private logs excluded. This scan is not a comprehensive security audit. |
| Dependency installation in a fresh Python 3.10 environment | `passed` | Python 3.10.4 / Windows; install exit 0; `pip check`: no broken requirements. Resolved versions saved in `requirements-lock.txt`. |
| `scripts/run_tests.py` on this package | `passed` | All nine allowlisted test files passed with assertions enabled, fake credentials and external-network blocking. |
| Local server startup and `/health` | `passed` | Real loopback HTTP to an owned ephemeral-port Uvicorn server returned 200 / `{"status":"ok"}`. Both POST routes rejected whitespace with 422 and returned a controlled missing-key 500. |
| Clean stop and restart of this package | `passed (assisted)` | `scripts/run_tests.py --smoke-repeat 2`: two separate fresh worker processes each started and stopped its owned server; combined result 11/11, exit 0. Existing user servers were not stopped. This is not a user-independent or separate-machine test. |
| Live `/ask` in this environment | `passed` | Deadline question returned HTTP 200 / success: 3 days from receipt, `p1-c1`, page 1; 2.24 s. The claim agrees with the bundled source. Two application-level Gemini requests. |
| Live `/requests` in this environment | `passed` | Fictional order 5 / Assaf perfume / broken bottle returned HTTP 200 / draft, the matching three input fields, title, description, and empty missing-fields list; 1.62 s. One generation request; no external ticket action. |
| Live insufficient-evidence check on this package | `not_run` | Covered by offline tests today; earlier live check retained above. Not repeated solely to fill the table. |
| n8n import and execution from this package | `not_run` | The exported three-node workflow was checked inactive, without credentials or pinned execution data. Earlier real n8n execution is recorded above; it was not re-imported today. |

The first server smoke attempt was blocked by the test guard when Python's Windows platform detection launched a standard-library OS-version query. The harness now primes that standard-library cache before installing its guard; child-process launches remain blocked while application tests run. All checks passed after that harness fix.

The release also handles `httpx`, `httpx2` and OS transport failures in the draft/legacy tool-calling client, with a 30-second request timeout and one attempt. Mocked regression cases cover these errors. The original development folder was left unchanged.

Live checks used local configuration excluded from Git and the distributable archive. No key values were displayed. The SDK emitted a nonfatal automatic-function-calling advisory during draft generation; the draft route supplied no execution tools and returned the expected structured result.

Do not run live checks merely to fill the table: they need a locally supplied key and consume provider quota. Offline tests alone do not establish live availability. A fresh installation, a server restart, and an independent user restart are different claims.

### Entry template

```text
Date/time:
Check and environment:
Command or manual steps:
Status: passed / failed / not_run / blocked
Actual result and evidence location:
Assistance used:
Provider calls, if measured:
Remaining limitation:
```

## What is not established

- The original twenty-case evaluation remains `not_run`; it is not included in the selected test run. Reserved evaluation cases were not used to tune this delivery.
- No training Gate pass is established by these checks. A guided successful demo is not an independent skills assessment.
- Safe external store/GitHub actions, explicit approval, durable duplicate prevention, and reconciliation after uncertain external outcomes are not delivered here.
- Production hosting, public authentication, service reliability, general answer accuracy, and broad prompt-injection resistance are not established.
- No independent user restart has been demonstrated. The assisted fresh-process server checks above must not be presented as the learner passing a Gate.

This is an assisted local prototype with bounded evidence, not a production-readiness certificate.
