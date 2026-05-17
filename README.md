<div align="center">

# ResuMatch AI

**Production-grade AI resume analyzer** — parse resumes, score them against one or many job descriptions, rank multiple candidates, and generate downloadable reports.

[![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](#)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47a248?logo=mongodb&logoColor=white)](#)
[![Tailwind](https://img.shields.io/badge/Tailwind-3-38bdf8?logo=tailwindcss&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#-license)

</div>

---

## Highlights

- **One-shot analysis pipeline** — upload a resume + JD(s), get back parsed data, skill match, ATS score, predicted roles, personalized recommendations, and a PDF report in a single request
- **Multi-JD analysis** — compare one resume against up to five job descriptions and surface the best fit
- **Bulk candidate comparison** — upload many resumes, rank them against one or more JDs
- **Weighted ATS scoring** — keywords (45%) · skills (25%) · sections (15%) · experience (15%) with full breakdown
- **Secure auth** — JWT sign-in/sign-up, bcrypt hashing, **OTP-based password reset** via Gmail SMTP, change-password flow
- **Rate-limited auth surface** — sliding-window limiter on login, register, and all OTP endpoints
- **Consistent error envelope** — every response carries a `request_id` that appears in server logs for easy tracing
- **Security defaults** — CSP, XFO, Referrer-Policy, Permissions-Policy, TrustedHost, env-driven CORS
- **Polished UI** — refined design system (buttons, cards, typography helpers), global gradient shell, password strength meter, live toast system, reduced-motion support

---

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | React 18 · React Scripts · TailwindCSS · Lucide icons · Axios · react-hot-toast |
| Backend | FastAPI · Uvicorn · Pydantic v2 · python-jose (JWT) · passlib+bcrypt · Motor (async Mongo driver) |
| Data | MongoDB Atlas · PDF/DOCX parsing (pdfplumber, python-docx, wordninja) |
| AI (optional) | OpenAI API — powers `/api/ai/*` bonus endpoints (cover letter, interview questions, resume-strength analysis) |
| Reports | ReportLab (PDF generation) |
| Email | Gmail SMTP (for OTP password reset) |

---

## Project structure

```
.
├── backend/
│   ├── main.py                      FastAPI app, middleware, CORS, security headers
│   ├── database.py                  Motor client + TTL indexes for OTP resets
│   ├── models/                      Pydantic request/response + DB models
│   ├── routers/
│   │   ├── auth_routes.py           Register, login, OTP reset, change password (rate-limited)
│   │   ├── analysis_routes.py       /api/analyze (single + bulk), history, report download
│   │   ├── profile_routes.py        Persistent user profile (resume upload, delete, stream)
│   │   └── ai_routes.py             Optional OpenAI-backed features
│   ├── services/
│   │   ├── resume_parser.py         PDF/DOCX → structured resume dict
│   │   ├── jd_processor.py          JD text/file → skills + keywords
│   │   ├── skill_extractor.py
│   │   ├── matching_engine.py       Case-insensitive, synonym-aware match scoring
│   │   ├── ats_scoring.py           4-component weighted ATS calculator
│   │   ├── role_prediction.py       Top-3 role fit from skills
│   │   ├── recommendation_engine.py Missing-skill → study plan & gap tips
│   │   ├── report_generator.py      ReportLab PDF composer
│   │   ├── email_service.py         Gmail SMTP sender for OTPs
│   │   ├── verdict_engine.py        Human-readable verdict ("Ready", "Needs work", etc.)
│   │   └── pipeline.py              Orchestrates: parse → match → ATS → roles → recs → verdict
│   ├── utils/
│   │   ├── rate_limit.py            In-memory sliding-window rate limiter
│   │   └── file_handler.py
│   └── data/                        skills.json · synonyms.json · role_profiles.json
│
├── frontend/
│   ├── tailwind.config.js           Design tokens (brand + accent ramps, shadows, gradients)
│   ├── postcss.config.js
│   └── src/
│       ├── App.jsx                  Auth gate + tab routing + Toaster
│       ├── styles/main.css          Component layer (.btn, .card, .badge, .input, typography)
│       ├── services/api.js          Axios client with auth interceptor
│       ├── components/
│       │   ├── ui/                  Card, ScoreCard, ProgressBar, Badge, EmptyState, Spinner
│       │   ├── layout/
│       │   │   ├── AppShell.jsx     Sidebar + gradient shell + profile/change-password modal
│       │   │   └── PageHeader.jsx   Reusable page header (eyebrow, title, subtitle, actions)
│       │   ├── auth/
│       │   │   ├── AuthPage.jsx     Split-hero login/register + password strength meter
│       │   │   └── ForgotPasswordModal.jsx
│       │   └── analysis/
│       │       └── JdListInput.jsx  Multi-JD input (paste or upload)
│       └── pages/
│           ├── Home.jsx             Landing with feature grid and workflow steps
│           ├── Dashboard.jsx        Profile view + resume upload
│           ├── Analyze.jsx          New analysis (1 resume × N JDs)
│           ├── BulkAnalyze.jsx      Compare resumes (M resumes × N JDs)
│           └── History.jsx          All past analyses, bulk-delete, PDF download
│
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick start

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+
- A MongoDB Atlas connection string (free tier works)
- *(optional)* OpenAI API key for `/api/ai/*` endpoints
- *(optional)* Gmail account + App Password for OTP password reset

### 1. Configure

```bash
cp .env.example .env
```

Edit `.env` with your real values. Minimum required:

| Variable | Purpose |
|---|---|
| `MONGODB_URL`              | Atlas connection string |
| `JWT_SECRET_KEY`           | Any 32+ char random string |
| `CORS_ALLOWED_ORIGINS`     | `http://localhost:3000` for dev |

For forgot-password OTP emails, also set:

| Variable | Purpose |
|---|---|
| `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` | Gmail + [App Password](https://myaccount.google.com/apppasswords) |

### 2. Backend

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn backend.main:app --reload
```

- API:  http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

Open http://localhost:3000.

---

## API surface

> Full, live OpenAPI schema at **`GET /openapi.json`** or explore it at **`/docs`**.

### Authentication

| Method | Path | Purpose | Rate limit |
|---|---|---|---|
| `POST` | `/api/auth/register`         | Sign up               | 5 / min |
| `POST` | `/api/auth/login`            | Sign in (JWT)         | 10 / min |
| `POST` | `/api/auth/change-password`  | Change (authenticated)| 5 / min |
| `POST` | `/api/auth/forgot-password`  | Start OTP flow        | 5 / 5min |
| `POST` | `/api/auth/verify-otp`       | Verify OTP → reset token | 10 / min |
| `POST` | `/api/auth/reset-password`   | Consume reset token   | 5 / min |
| `PUT`  | `/api/auth/users/{id}`       | Update profile info   | — |

### Resume profile

| Method | Path | Purpose |
|---|---|---|
| `POST`   | `/api/profile/upload`      | Upload / replace user resume |
| `GET`    | `/api/profile`             | Fetch parsed profile |
| `DELETE` | `/api/profile`             | Delete stored profile |
| `GET`    | `/api/profile/resume/file` | Stream original resume bytes |

### Analysis pipeline

| Method | Path | Purpose |
|---|---|---|
| `POST`   | `/api/analyze`                      | **Single resume** × one JD → full analysis |
| `POST`   | `/api/analyze/bulk`                 | **Many resumes** × one JD → ranked results |
| `GET`    | `/api/analyze/history`              | User's history |
| `DELETE` | `/api/analyze/history/{analysis_id}`| Delete one |
| `POST`   | `/api/analyze/history/delete`       | Bulk-delete or delete-all |
| `GET`    | `/api/analyze/{analysis_id}/report` | Download PDF report |

### Optional AI endpoints

| Path | Returns |
|---|---|
| `/api/ai/status`, `/api/ai/features` | Capability probing |
| `/api/ai/cover-letter`               | Tailored cover letter |
| `/api/ai/interview-questions`        | Top N interview questions |
| `/api/ai/resume-strength`            | GPT-scored strength analysis |
| `/api/ai/improvements`               | Targeted suggestions |
| `/api/ai/predict-roles`              | LLM-based role predictions |
| `/api/ai/semantic-match`             | Embedding-based skill match |

---

## Pipeline flow

```
POST /api/analyze  (multipart: resume_file + jd_text | jd_file)
        │
        ├──► parse_resume()          PDF/DOCX → structured dict
        ├──► process_job_description() text/file → skills + keywords
        │
        ▼
   pipeline.run_full_analysis()
        ├── match score        (matching_engine)
        ├── ATS score          (ats_scoring; 4 weighted components)
        ├── role prediction    (role_prediction)
        ├── recommendations    (recommendation_engine)
        └── verdict            (verdict_engine — "Ready", "Almost there", "Needs work", …)
        │
        ▼
   Persist → MongoDB (resumes · job_descriptions · analysis_results)
        │
        ▼
   AnalysisResponse → frontend renders result dashboard
```

---

## MongoDB collections

- **users** — auth records. Unique index on `email`.
- **user_profiles** — one resume per user (dashboard view).
- **resumes** — every uploaded resume + parsed `resume_data`.
- **job_descriptions** — JDs with parsed `jd_data`.
- **analysis_results** — per-analysis snapshot (scores, missing skills, recs, roles, verdict).
- **password_resets** — active OTP sessions, with TTL index so entries auto-expire.

Indexes are ensured on startup — see `backend/database.py`.

---

## Security

| Control | Where |
|---|---|
| **JWT auth** with env-driven secret | `backend/routers/auth_routes.py` |
| **bcrypt** password hashing via passlib | `auth_routes.py` |
| **Rate limiting** (sliding window) on all auth endpoints | `backend/utils/rate_limit.py` |
| **OTP-based password reset** with TTL, max attempts, resend cooldown | `auth_routes.py`, `email_service.py` |
| **Security headers** (CSP, XFO, nosniff, Referrer-Policy, Permissions-Policy) | `main.py` middleware |
| **Trusted hosts + env-driven CORS** | `main.py` |
| **Consistent error envelope** with `request_id` in every response | `main.py` exception handlers |
| **No error leakage in production** — details hidden when `APP_ENV=production` | `main.py` |
| **Max upload size** configurable via `MAX_UPLOAD_SIZE_BYTES` | — |
| **Auto-logout** on stale/invalid JWT from any route | `frontend/src/services/api.js` interceptor |

Before deploying to production:
1. Set `JWT_SECRET_KEY` to a long, random string (at least 32 chars).
2. Set `APP_ENV=production` to hide internal error messages.
3. Set `MONGODB_REQUIRED=true` so the server fails fast if Mongo is unreachable.
4. Lock down `CORS_ALLOWED_ORIGINS` and `TRUSTED_HOSTS` to your real domains.
5. Enable `TRUST_PROXY_HEADERS=true` only if running behind a trusted reverse proxy.

---

## Deployment

- **Backend**: Render, Railway, Fly.io, or any Python-capable host. Deploy from a `gunicorn` + `uvicorn.workers.UvicornWorker` config for production. Provide all env vars from `.env.example`.
- **Frontend**: `npm run build` → deploy the generated `frontend/build/` to Vercel / Netlify / Cloudflare Pages. Set `REACT_APP_API_BASE_URL` at build time to your backend URL.
- **Database**: MongoDB Atlas (free M0 tier is sufficient to start).

---

## Testing

```bash
pytest tests/
```

Currently covers edge cases around file validation, JWT auth, and pipeline output shape. A more exhaustive test suite is on the roadmap.

---

## Roadmap

- [ ] Unit-test coverage for `pipeline.run_full_analysis`
- [ ] End-to-end Playwright tests for the upload → analyze → download flow
- [ ] Containerized deployment (Dockerfile + `docker-compose.yml`)
- [ ] Migration to Vite (CRA is deprecated)
- [ ] Redis-backed rate limiter for multi-worker deployments
- [ ] Stripe-backed billing tier for premium AI features

---

## License

[MIT](LICENSE) © 2026 ResuMatch AI
