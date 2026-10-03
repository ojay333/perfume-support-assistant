# Perfume Support — Local RAG Demo

Arabic customer-support answers with traceable policy excerpts, structured follow-up drafts, and an optional n8n workflow.

This is a small **local prototype**, not a production store integration. It uses a two-page sample policy and five indexed chunks. It does not approve returns, create store orders, or move money.

## What is included

- **Policy Q&A:** retrieve relevant PDF excerpts, generate an Arabic answer, and return chunk IDs, page numbers, and source text. Return an insufficient-evidence message when the retrieved context cannot answer the question.
- **Structured drafts:** extract follow-up details and identify missing information without submitting a request to a store.
- **Local automation:** an optional manual n8n workflow sends a question to the API; Python handles retrieval and Gemini calls.
- **Tests and evidence:** local mocked tests, documented live checks, and explicit limits on what has been verified.

## Quick start — Windows PowerShell

Open PowerShell in this package's root directory. Install Python 3.10 first if it is not available.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` also applies `requirements-lock.txt`, recording the resolved dependencies verified on Python 3.10.4 / Windows. No upgrade of an existing environment is required: use this separate environment.

For live Gemini calls, manually copy `customer_support_agent/.env.example` to `customer_support_agent/.env` if that file does not already exist. Enter your own `GOOGLE_API_KEY` locally and check the model setting. Never commit or share `.env`, credentials, or n8n account data. No working API key is included.

Start the API from the same directory:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir customer_support_agent --host 127.0.0.1 --port 8001
```

Open [interactive API docs](http://127.0.0.1:8001/docs). Keep the terminal running; press `Ctrl+C` to stop it. Binding to `127.0.0.1` keeps this demo local to your computer.

If port 8001 is already in use, do not start a second copy on it. Stop your earlier server with `Ctrl+C` in its own terminal, or choose a different port and update both the browser URL and the optional n8n HTTP-node URL. Do not stop an unidentified process.

| Endpoint | Purpose | Important boundary |
|---|---|---|
| `GET /health` | Check that the API is running | Does not test Gemini or answer quality |
| `POST /ask` | Policy answer with sources, or `insufficient_evidence` | No tool execution or store action |
| `POST /requests` | Structured follow-up `draft` | Not approval or external submission |

Both POST endpoints accept a JSON object such as `{"user_input": "ما مهلة تقديم متابعة لعطر وصل مكسورًا؟"}`. Inputs must be nonblank and at most 500 characters. Validation failures return HTTP 422; handled retrieval or generation failures return HTTP 500. A deliberate insufficient-evidence answer returns HTTP 200.

## Run local tests

From the package root, without starting the API:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_tests.py
```

To also verify two fresh local server starts and stops, without any real API key:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_tests.py --smoke-repeat 2
```

The selected tests use mocked Gemini responses and the bundled policy files; they do not make live provider requests. They are **not** the original twenty-case evaluation suite. See [verification status](docs/VERIFICATION.md) for historical evidence and the current package's verification status.

For an explicit live question, using your own key and quota:

```powershell
.\.venv\Scripts\python.exe .\customer_support_agent\manual_rag_test.py --question "ما مهلة تقديم متابعة لعطر وصل مكسورًا؟"
```

A normal RAG question makes two Gemini calls: one question embedding and one answer generation. The included index avoids re-embedding the document on every question. If you change the PDF or chunks, review the extracted text and deliberately rebuild the index; do not bypass the stale-index check.

From the package root, rebuilding uses these commands. The first replaces the generated chunks; the second replaces the index and consumes Gemini quota. Keep the original PDF and inspect the extracted text before rebuilding:

```powershell
.\.venv\Scripts\python.exe .\customer_support_agent\prepare_policy.py
.\.venv\Scripts\python.exe .\customer_support_agent\build_index.py
```

Git attributes preserve the exact PDF and JSON bytes used by the index fingerprints. Do not format those data files merely to change line endings.

## Demo and scope

Follow the [Arabic demo guide](docs/DEMO.md). The optional [n8n guide](customer_support_agent/automation/N8N_DEMO.md) explains importing and manually running the workflow; n8n is not bundled or required for the API demo.

On 3 October 2026, this delivery installed successfully in a fresh Python 3.10.4 environment: nine offline test files and two owned local server start/stop checks passed. A live `/ask` check returned a supported 3-day answer, and `/requests` returned a structured draft. See the verification record for exact scope, earlier n8n evidence and unrun evaluations. These are assisted checks, not an independent user assessment or a production guarantee.

The project was developed with substantial instructional and implementation assistance. Citation-ID validation cannot prove that every generated claim is supported. The original twenty-case evaluation remains unrun; no training Gate pass is claimed by this package. Safe external actions and production deployment remain outside this delivery's scope.
