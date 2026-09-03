# MediExtractAI

**Turn free-text clinical notes into structured, analysis-ready tables — with AI.**

🔗 **Live demo: [http://140.238.101.112](http://140.238.101.112)** — open, no sign-in, synthetic data only.

A full-stack web application that connects to an existing clinical notes database (or takes uploaded `.txt` / `.docx` / `.pdf` documents), lets a user define an output schema on the fly, and uses an LLM to extract structured rows — which a clinician then corrects and signs off before they are allowed to leave as anything but a draft.

Built by a healthcare data engineer to explore how LLMs can accelerate one of the most manual jobs in clinical data work: turning unstructured narrative notes into usable datasets.

> **Note on data:** this project is developed and demonstrated with **synthetic clinical notes only**. It has never processed real patient data. The architecture (OIDC auth, RBAC, audit logging, private networking) is designed so it *could* run in a governed healthcare environment, but the public demo runs in open demo mode.

## Try the demo

The demo carries two data sources with deliberately different schemas, so the same UI reads both without a code change:

| Data source | Table | note id | patient | note text | note type |
|---|---|---|---|---|---|
| Demo clinical notes | `medical_notes` | `id` | `patient_id` | `note_text` | `specialty` |
| Clinic Letters (legacy) | `clinical_documents` | `doc_id` | `mrn` | `doc_body` | `service` |

The note type column is optional in the mapping. Where a source has one, the browser
offers a type filter built from the values actually in that column — what counts as a
note type is whatever the customer's system puts there, and it differs between
deployments of the same vendor's software.

Use **View as** in the header to switch between Admin, Clinician and ReadOnly. The roles are enforced by the API, not hidden in the UI — a Clinician really does get a 403 from the data source endpoints, and a ReadOnly viewer sees every run but is given no way to approve one.

A run through the demo: pick a few notes, define a couple of columns, press **Run extraction**. The table appears over the page as a **draft** — correct a value and the model's original answer stays beside it, approve or reject rows, then sign the run off. Try exporting before you sign: the CSV comes out named `-DRAFT` with a review-status column on every row. Everything you did is in **Review**, with the same run, its history and its signature.

The synthetic notes are written to contain what makes clinical extraction hard: negation, ex-smoker versus current smoker, family history that belongs to someone else, and UK dosing abbreviations (`BD`, `OD`, `TDS`, `PRN`).

## Features

- **Data sources** — register a clinical database and map its columns to what the app needs. No two hospitals name their notes table the same way, so the mapping is configuration rather than a code change.
- **Dialect portability** — queries are built with SQLAlchemy Core, so the same code runs against PostgreSQL, SQL Server or a SQLite extract.
- **Note browser with filters** — narrow by note type, clinician and date range before searching the text. Clinical systems keep nursing, outpatient and inpatient notes in one place, so filtering down is how anyone actually finds a note; keyword search is the fallback, not the opening move.
- **Dynamic schema builder** — define output columns, types and extraction instructions in the UI.
- **AI extraction** — Google Gemini (free tier) or Azure OpenAI, selected by config. Notes are extracted concurrently behind a bounded semaphore.
- **Row provenance** — every extracted row carries the note and patient it came from. One note can produce several rows, so this is the only thing that keeps a row attributable.
- **Review and sign-off** — every extraction is persisted as a *draft*. A clinician corrects what the model got wrong, approves or rejects each row, and signs the run off; signed-off runs are read-only until explicitly reopened. See [The workflow](#the-workflow).
- **Corrections, not re-runs** — a wrong value is edited in place. The model's original answer is kept beside it, every change is recorded against the person who made it, and one click puts the model's answer back.
- **File upload** — parse `.txt`, `.doc/.docx`, `.pdf` into plain text.
- **Gated export** — CSV or Excel, produced from a stored run rather than from what the browser posts. An unsigned run still exports, but labelled: `-DRAFT` in the filename, a review-status column on every row, and a sheet in the workbook saying so.
- **Role separation** — Admin configures data sources; Clinician browses and extracts; ReadOnly can neither.
- **Audit trail** — logging of who accessed what and when, with no note content in the logs.

## The workflow

The extraction is not the product; the reviewed dataset is. So the pipeline is shaped like a document review, not a batch job:

```
select notes (database)  │  upload documents (personal scope)
            ↓
  run  →  saved immediately as a DRAFT, every row pending
            ↓
  review: correct a value (the model's answer is kept beside it)
          approve or reject each row · reopen anything already decided
            ↓                              ↘ wrong schema or wrong notes?
  sign off (clinician) — rows freeze          re-run: a new run to compare against,
            ↓                                 never an overwrite
  export: signed-off runs come out clean; anything else comes out marked DRAFT
```

Three gates, deliberately kept separate:

| | Gated? | Why |
|---|---|---|
| Saving a draft to our database | No | Not saving is what loses corrections and leaves no trail. Saved is not the same as blessed. |
| Leaving the system (CSV / Excel / downstream) | Yes | This is where data becomes something other people will act on. |
| Writing back into the hospital system | Not built | Structured data flowing back into a clinical record changes the regulatory position; that is a deliberate decision, not an oversight. |

Approval is enforced by the API, not by the UI: exports are addressed by run id and the server decides what may leave and how the file is labelled. `REQUIRE_SEPARATE_APPROVER` (off in the demo, on in a governed deployment) additionally stops anyone signing off a run they started themselves.

## Architecture

```
React 18 + TypeScript SPA ──▶ nginx ──▶ FastAPI (async)
                                          ├─▶ Gemini API / Azure OpenAI
                                          ├─▶ App database   (PostgreSQL)  runs, rows, revisions,
                                          │                                audit log, data sources
                                          ├─▶ Notes database (PostgreSQL)  the customer's system,
                                          │                                read-only
                                          └─▶ Local file parsing (PyMuPDF, python-docx)
```

The two databases are deliberately separate — separate instances, not two schemas in one. In a real deployment the notes live in a system we do not own and hold read-only credentials to; putting our audit log inside the customer's estate is exactly what a governance review would object to. Development collapses the app database to a SQLite file so a clone runs with no external service; the deployment does not.

- **Backend:** FastAPI, SQLAlchemy 2 (async), Pydantic v2
- **Frontend:** React 18, TypeScript, Vite, Tailwind
- **Infra:** Docker Compose, nginx; original Azure IaC (Bicep) kept under `infra/azure/`

## Quick start (development)

Development runs against SQLite — no Postgres needed. The notes database falls back to
`DATABASE_URL` when `NOTES_DATABASE_URL` is unset, which is the dialect portability doing
real work rather than being claimed.

```bash
git clone https://github.com/Gouqiqiqiqi/MediExtractAI.git
cd MediExtractAI
cp backend/.env.example backend/.env   # add your GEMINI_API_KEY, leave NOTES_DATABASE_URL blank
docker compose -f infra/docker-compose.yml up --build
```

Then seed the synthetic notes into the SQLite file:

```bash
docker compose -f infra/docker-compose.yml exec backend python scripts/seed_notes.py
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

Or run natively: `uvicorn app.main:app --reload` in `backend/`, `npm run dev` in `frontend/`.

## Deploy (single VM — e.g. OCI Always Free)

Runs on an Oracle Cloud Always Free ARM VM (Ubuntu). All images are multi-arch. The
production compose file adds two PostgreSQL services: `app-db`, which holds the audit
trail and review state, and `notes-db`, which stands in for the customer's clinical
system. Neither publishes a port — they are reachable only from the compose network.

```bash
# on the VM
sudo apt update && sudo apt install -y docker.io docker-compose-v2
git clone https://github.com/Gouqiqiqiqi/MediExtractAI.git && cd MediExtractAI

# the two database passwords, read by docker compose
{ echo "NOTES_DB_PASSWORD=$(openssl rand -hex 24)"
  echo "APP_DB_PASSWORD=$(openssl rand -hex 24)"; } > .env && chmod 600 .env

cp backend/.env.example backend/.env
nano backend/.env   # GEMINI_API_KEY, a random APP_SECRET_KEY, and NOTES_DATABASE_URL
                    # with the password you just generated. Keep DEMO_MODE=true.

sudo docker compose up -d --build
sudo docker compose exec backend python scripts/seed_notes.py
```

Open port **80** in two places — they are independent and both are required:

1. The VM's own firewall: `sudo iptables -I INPUT -p tcp --dport 80 -m state --state NEW -j ACCEPT`, then `sudo netfilter-persistent save`
2. The OCI security list ingress rule — the port goes in **Destination** Port Range, not Source

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `true` | `true`: no auth, role chosen by the viewer, synthetic data only. `false`: OIDC (Azure AD) |
| `APP_SECRET_KEY` | — | Also derives the key that encrypts stored data source passwords. Changing it invalidates them. |
| `AI_PROVIDER` | `gemini` | `gemini` or `azure_openai` |
| `GEMINI_API_KEY` | — | Free key from https://aistudio.google.com/apikey |
| `GEMINI_MODEL` | `gemini-3.5-flash` | See the quota note below before changing |
| `AI_FALLBACK_MODELS` | Groq, Mistral, then two more Gemini models | Models to rotate to when the one above is rate limited, in order. `provider:model`, or a bare model name for `AI_PROVIDER`'s provider. |
| `GROQ_API_KEY` / `MISTRAL_API_KEY` | — | Free keys, no card. Blank means that provider is dropped from the chain at startup. |
| `AI_VISION_MODELS` | — | Extra models that can read page images, as `provider:model`. Only needed for a vision model this app does not recognise by name — see "Scanned documents" below. |
| `PDF_RENDER_DPI` / `PDF_RENDER_MAX_PAGES` | `150` / `8` | How a scanned PDF is rendered for the model to read. |
| `DATABASE_URL` | SQLite | The app's own database: extraction runs, their rows and revisions, audit log, data source registry. The production compose file overrides it with the `app-db` Postgres service. |
| `REQUIRE_SEPARATE_APPROVER` | `false` | `true`: the person who ran an extraction may not sign it off. Off in the demo, which has one user. |
| `NOTES_DATABASE_URL` | falls back to `DATABASE_URL` | The clinical notes database. Registered as the default data source on first start. |
| `DEMO_ALLOWED_DB_HOSTS` | `notes-db,localhost,127.0.0.1` | Hosts a demo deployment may connect a data source to. Ignored when `DEMO_MODE=false`. |

### Scanned documents

Not every PDF is text. A scan, a photographed note, or an image saved as a PDF has no
text layer at all, and a text extractor returns an empty string for it — which is worse
than an error, because an empty note reaches the model looking like a successful upload.

So a PDF whose text layer is empty (or thin enough to be only a scanner's header and
page numbers) is rendered to page images instead, and those pages are sent to the model
to read directly. No OCR step: the model reads the page.

That changes which models may serve the note. The chain is filtered to the ones that
accept images before any of the rotation logic runs, so a scan is never offered to a
text-only model — the default chain's `groq:openai/gpt-oss-120b` keeps serving text
notes and is simply not a candidate for scanned ones. It is a capability, not an
availability: a model skipped this way is *not* put on a cooldown, because it is still
the right answer for the next note that is text. `GET /api/v1/extraction/models` reports
`supports_vision` per model, and a scan with no vision-capable model in the chain fails
with a message that says so rather than a 400 from the provider.

Two things are deliberately conservative here. Models are recognised as vision-capable
by name, and an unrecognised one is assumed text-only — a false positive costs a 400
that the rotation reads as a broken model and parks for the session, a false negative
only costs an unused option. And the prompt for a scan tells the model to return `null`
for anything illegible rather than guess: in a clinical record an omitted value gets
checked by a human and an invented one does not. Rows from a scan should be reviewed
before they are approved; the uploader says so, and the pages the model was given are
shown next to the result.

### Free-tier quota, and what happens when it runs out

One API request is made per note, so extracting 20 notes costs 20 requests. Free-tier
quotas are **per model and per day**, and they vary sharply: `gemini-2.5-flash` allows
20 requests a day, which a single demo session exhausts. Check your key at
https://ai.dev/rate-limit.

So the extractor holds a chain of models rather than one — `GEMINI_MODEL` followed by
`AI_FALLBACK_MODELS` — and rotates down it. Because the quota is counted per model,
the next model in the chain is a fresh quota; and because the chain crosses providers,
so is the next provider. The default chain is:

```
gemini-3.5-flash → groq:openai/gpt-oss-120b → mistral:mistral-small-latest
                 → gemini-3.1-flash-lite → gemini-2.5-flash
```

Groq and Mistral speak the OpenAI chat-completions API, so they share one adapter —
adding another provider of that kind is an endpoint URL and an API key, not an
integration. A provider whose key is unset is dropped from the chain at startup, so
the defaults are safe to ship unset.

A 429 puts that model on a cooldown the rest of the batch sees, so hitting the limit
costs one request rather than one per remaining note. How long the cooldown lasts comes
from the provider's own answer: Google's error says whether the quota that was hit is
per-minute or per-day, and only the second means "not today". A per-minute limit with
nowhere to rotate to is waited out; a spent daily quota is not, and returns a 503 saying
which models are exhausted rather than holding the request open for hours. A model that
answers 404 — a retired model name, the other way a demo goes quiet — is dropped from
the chain for the life of the process, with the reason in the log.

```bash
curl -s localhost:8000/api/v1/extraction/models -H 'X-Demo-Role: Admin' | python3 -m json.tool
```

shows the chain in order and, for anything on cooldown, why and for how long.

## Before a demo

```bash
make preflight            # or: scripts/preflight.sh [base-url]
```

The failures that ruin a live demo are the quiet ones: the site loads, the notes
list looks right, and extraction returns nothing because a model was retired or
yesterday's testing spent the day's quota. So the check presses the button —
site, bundle, API, data source, role separation, the model chain, and one real
extraction whose output it inspects. It then checks the review gate on the
deployment itself: the extraction was persisted as a draft, an approved-rows
export of it is refused, a draft export is labelled `DRAFT`. The run it made is
discarded afterwards — a pre-flight check is not someone's work to review.
Exit code 0 means the demo is ready.

Extraction is bounded on both ends so a failure is legible rather than a hung
tab: `AI_REQUEST_TIMEOUT_SECONDS` per model call, `AI_DEADLINE_SECONDS` for the
whole request. The deadline sits inside the timeouts in front of it — nginx and
the browser client both cut at 120s — because a request killed out there
surfaces as a generic network error, while one that ends inside the app returns
the reason, and the UI shows that reason instead of "extraction failed".

## Security posture

Demo mode is intentionally open, and the data is synthetic. Three things are still done
properly, because a public unauthenticated page that accepts database connection details
would otherwise be a liability:

- **Credentials** — data source passwords are encrypted at rest with a key derived from
  `APP_SECRET_KEY`. No response model returns a password or an assembled connection string.
- **SSRF** — while `DEMO_MODE` is on, new data sources may only point at an allow-listed
  host. Unauthenticated plus "connect to any host you like" is an SSRF primitive and a
  credential-harvesting form in one.
- **Injection** — table and column names are validated against an identifier pattern
  before they reach a SQLAlchemy `Table`, on top of SQLAlchemy's own quoting.

For a governed deployment the codebase also includes OIDC token validation (RS256/JWKS),
role-based access control, security headers and CSP, upload size and type limits, and an
audit trail — written for every run, correction, approval and export, in the same
transaction as the act it records, and never containing note content. `infra/azure/` retains the original Bicep
templates for a private-endpoint Azure deployment.

## Project structure

```
MediExtractAI/
├── backend/
│   ├── app/            # FastAPI app (api / core / models / services)
│   ├── scripts/        # synthetic notes + seeding
│   └── tests/
├── frontend/src/       # React + TS SPA (api / auth / components / lib / pages)
│   └── components/Review/   # the review surface: table, sign-off, export, pop-up
├── infra/              # dev compose, nginx, Azure Bicep (legacy)
└── docker-compose.yml  # production: frontend + backend + notes database
```

## License

MIT
