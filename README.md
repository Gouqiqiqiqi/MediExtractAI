# MediExtractAI

**Turn free-text clinical notes into structured, analysis-ready tables — with AI.**

A full-stack web application that lets a user upload medical documents (`.txt`, `.docx`, `.pdf`) or point at a notes database, define an output schema on the fly, and use an LLM to extract structured rows they can review, correct, and export (CSV / Excel / FHIR JSON).

Built by a healthcare data engineer to explore how LLMs can accelerate one of the most manual jobs in clinical data work: turning unstructured narrative notes into usable datasets.

> **Note on data:** this project is developed and demonstrated with **synthetic clinical notes only**. It has never processed real patient data. The architecture (OIDC auth, RBAC, audit logging, private networking) is designed so it *could* run in a governed healthcare environment, but the public demo runs in open demo mode.

## Features

- **File Upload** — parse `.txt`, `.doc/.docx`, `.pdf` into plain text
- **Database Reader** — connect to an existing notes database and extract in bulk
- **Dynamic Schema Builder** — define output columns and data types in the UI
- **AI-Powered Extraction** — Google Gemini (free tier) or Azure OpenAI, selected by config
- **Editable Results Table** — review, correct, and approve extracted rows
- **Export** — CSV, Excel, or FHIR JSON
- **Audit Trail** — logging of who accessed what and when (no patient data in logs)

## Architecture

```
React 18 + TypeScript SPA ──▶ nginx ──▶ FastAPI (async)
                                          ├─▶ Gemini API / Azure OpenAI
                                          ├─▶ SQLite (default) / any SQLAlchemy DB
                                          └─▶ Local file parsing (PyMuPDF, python-docx)
```

- **Backend:** FastAPI, SQLAlchemy 2 (async), Pydantic v2
- **Frontend:** React 18, TypeScript, Vite, Tailwind, TanStack-style hooks
- **Infra:** Docker Compose, nginx; original Azure IaC (Bicep) kept under `infra/azure/`

## Quick Start (Development)

```bash
git clone <repo-url>
cd MediExtractAI
cp backend/.env.example backend/.env   # add your GEMINI_API_KEY
docker compose -f infra/docker-compose.yml up --build
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

Or run natively: `uvicorn app.main:app --reload` in `backend/`, `npm run dev` in `frontend/`.

## Deploy (single VM — e.g. OCI Always Free)

Tested on an Oracle Cloud Always Free ARM VM (Ubuntu). All images are multi-arch.

```bash
# on the VM
sudo apt update && sudo apt install -y docker.io docker-compose-v2
git clone <repo-url> && cd MediExtractAI
cp backend/.env.example backend/.env
nano backend/.env        # set GEMINI_API_KEY + APP_SECRET_KEY; keep DEMO_MODE=true
sudo docker compose up -d --build
```

Then open port 80 in the OCI security list / VCN ingress rules, and browse to the VM's public IP.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `true` | `true`: no auth, demo user, synthetic data only. `false`: OIDC (Azure AD) |
| `AI_PROVIDER` | `gemini` | `gemini` or `azure_openai` |
| `GEMINI_API_KEY` | — | Free key from https://aistudio.google.com/apikey |
| `DATABASE_URL` | SQLite | Any SQLAlchemy async URL |

## Security posture

Demo mode is intentionally open (synthetic data only). For a governed deployment the codebase already includes: OIDC token validation (RS256/JWKS), role-based access control (Admin / Clinician / ReadOnly), security headers + CSP, upload size/type limits, and an audit log model that never stores note content. `infra/azure/` retains the original Bicep templates for a private-endpoint Azure deployment.

## Project Structure

```
MediExtractAI/
├── backend/            # FastAPI app (api / core / models / services) + tests
├── frontend/           # React + TS SPA (api / auth / components / pages)
├── infra/              # docker-compose (dev), nginx, Azure Bicep (legacy)
└── docker-compose.yml  # production single-VM deployment
```

## License

MIT
