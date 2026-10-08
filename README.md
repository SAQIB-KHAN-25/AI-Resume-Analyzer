<div align="center">

# ResuMatch AI

**Production-grade AI resume analyzer** — parse resumes, score them against one or many job descriptions, rank multiple candidates, and generate downloadable reports.

[Live demo](https://ai-resume-analyzer-frontend-px1q.onrender.com)

[![React](https://img.shields.io/badge/React-18-61dafb?logo=react\&logoColor=white)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi\&logoColor=white)](#)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47a248?logo=mongodb\&logoColor=white)](#)
[![Tailwind](https://img.shields.io/badge/Tailwind-3-38bdf8?logo=tailwindcss\&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#-license)

</div>

---

## Highlights

* **One-shot analysis pipeline** — upload a resume + JD(s), get back parsed data, skill match, ATS score, predicted roles, personalized recommendations, and a PDF report in a single request
* **Multi-JD analysis** — compare one resume against up to five job descriptions and surface the best fit
* **Bulk candidate comparison** — upload many resumes, rank them against one or more JDs
* **Weighted ATS scoring** — keywords (45%) · skills (25%) · sections (15%) · experience (15%) with full breakdown
* **Secure auth** — JWT sign-in/sign-up, bcrypt hashing, **OTP-based password reset** via Gmail SMTP, change-password flow
* **Rate-limited auth surface** — sliding-window limiter on login, register, and all OTP endpoints
* **Consistent error envelope** — every response carries a `request_id` that appears in server logs for easy tracing
* **Security defaults** — CSP, XFO, Referrer-Policy, Permissions-Policy, TrustedHost, env-driven CORS
* **Polished UI** — refined design system (buttons, cards, typography helpers), global gradient shell, password strength meter, live toast system, reduced-motion support

---

## Tech Stack

| Layer         | Stack                                                                                                         |
| ------------- | ------------------------------------------------------------------------------------------------------------- |
| Frontend      | React 18 · React Scripts · TailwindCSS · Lucide icons · Axios · react-hot-toast                               |
| Backend       | FastAPI · Uvicorn · Pydantic v2 · python-jose (JWT) · passlib+bcrypt · Motor (async Mongo driver)             |
| Data          | MongoDB Atlas · PDF/DOCX parsing (pdfplumber, python-docx, wordninja)                                         |
| AI (optional) | OpenAI API — powers `/api/ai/*` bonus endpoints (cover letter, interview questions, resume-strength analysis) |
| Reports       | ReportLab (PDF generation)                                                                                    |
| Email         | Gmail SMTP (for OTP password reset)                                                                           |

---

## Project Structure

```text
.
├── backend/
│   ├── main.py                      # FastAPI app, middleware, CORS, security headers
│   ├── database.py                  # Motor client + TTL indexes for OTP resets
│   ├── models/                      # Pydantic request/response + DB models
│   ├── routers/
│   │   ├── auth_routes.py           # Register, login, OTP reset, change password
│   │   ├── analysis_routes.py       # /api/analyze, history, report download
│   │   ├── profile_routes.py        # Persistent user profile
│   │   └── ai_routes.py             # Optional OpenAI-backed features
│   ├── services/
│   │   ├── resume_parser.py         # PDF/DOCX → structured resume dict
│   │   ├── jd_processor.py          # JD text/file → skills + keywords
│   │   ├── skill_extractor.py
│   │   ├── matching_engine.py       # Case-insensitive, synonym-aware match scoring
│   │   ├── ats_scoring.py           # 4-component weighted ATS calculator
│   │   ├── role_prediction.py       # Top-3 role fit from skills
│   │   ├── recommendation_engine.py # Missing-skill → study plan & gap tips
│   │   ├── report_generator.py      # ReportLab PDF composer
│   │   ├── email_service.py         # Gmail SMTP sender for OTPs
│   │   ├── verdict_engine.py        # Human-readable verdict
│   │   └── pipeline.py              # Full analysis orchestration
│   ├── utils/
│   │   ├── rate_limit.py            # In-memory sliding-window rate limiter
│   │   └── file_handler.py
│   └── data/                        # skills.json · synonyms.json · role_profiles.json
│
├── frontend/
│   ├── tailwind.config.js           # Design tokens
│   ├── postcss.config.js
│   └── src/
│       ├── App.jsx                  # Auth gate + tab routing + Toaster
│       ├── styles/main.css          # Component styles
│       ├── services/api.js          # Axios client with auth interceptor
│       ├── components/
│       │   ├── ui/                  # Card, ScoreCard, ProgressBar, Badge, etc.
│       │   ├── layout/
│       │   │   ├── AppShell.jsx
│       │   │   └── PageHeader.jsx
│       │   ├── auth/
│       │   │   ├── AuthPage.jsx
│       │   │   └── ForgotPasswordModal.jsx
│       │   └── analysis/
│       │       └── JdListInput.jsx
│       └── pages/
│           ├── Home.jsx
│           ├── Dashboard.jsx
│           ├── Analyze.jsx
│           ├── BulkAnalyze.jsx
│           └── History.jsx
│
├── requirements.txt
├── .env.example
└── README.md
```

> **Testing note:** The repository currently does **not** contain a dedicated `tests/` directory or automated pytest test suite.

---

## Quick Start

### Prerequisites

* Python 3.11 or 3.12
* Node.js 18+
* A MongoDB Atlas connection string
* Optional: OpenAI API key for `/api/ai/*` endpoints
* Optional: Gmail account + App Password for OTP password reset

---

### 1. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with your real values.

Minimum required variables:

| Variable               | Purpose                                                  |
| ---------------------- | -------------------------------------------------------- |
| `MONGODB_URL`          | MongoDB Atlas connection string                          |
| `JWT_SECRET_KEY`       | Random secret used for JWT signing                       |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origin, such as `http://localhost:3000` |

For forgot-password OTP emails, also configure:

| Variable    | Purpose                                   |
| ----------- | ----------------------------------------- |
| `SMTP_USER` | Gmail account used for sending OTP emails |
| `SMTP_PASS` | Gmail App Password                        |
| `SMTP_FROM` | Sender email address                      |

> Never commit `.env` or real credentials to the repository.

---

## Backend

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

### Activate the Environment

#### Windows

```powershell
.venv\Scripts\activate
```

#### macOS/Linux

```bash
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Start the Backend

```bash
uvicorn backend.main:app --reload
```

The backend will be available at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

Health endpoint:

```text
http://localhost:8000/health
```

---

## Frontend

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### Start the Frontend

```bash
npm start
```

The frontend will be available at:

```text
http://localhost:3000
```

---

## API Surface

The complete OpenAPI schema is available at:

```text
GET /openapi.json
```

Interactive API documentation:

```text
/docs
```

---

### Authentication

| Method | Path                        | Purpose                    | Rate Limit |
| ------ | --------------------------- | -------------------------- | ---------- |
| `POST` | `/api/auth/register`        | Sign up                    | 5 / min    |
| `POST` | `/api/auth/login`           | Sign in (JWT)              | 10 / min   |
| `POST` | `/api/auth/change-password` | Change password            | 5 / min    |
| `POST` | `/api/auth/forgot-password` | Start OTP flow             | 5 / 5 min  |
| `POST` | `/api/auth/verify-otp`      | Verify OTP                 | 10 / min   |
| `POST` | `/api/auth/reset-password`  | Reset password             | 5 / min    |
| `PUT`  | `/api/auth/users/{id}`      | Update profile information | —          |

---

### Resume Profile

| Method   | Path                       | Purpose                      |
| -------- | -------------------------- | ---------------------------- |
| `POST`   | `/api/profile/upload`      | Upload / replace user resume |
| `GET`    | `/api/profile`             | Fetch parsed profile         |
| `DELETE` | `/api/profile`             | Delete stored profile        |
| `GET`    | `/api/profile/resume/file` | Stream original resume bytes |

---

### Analysis Pipeline

| Method   | Path                                 | Purpose                                |
| -------- | ------------------------------------ | -------------------------------------- |
| `POST`   | `/api/analyze`                       | Single resume × one JD → full analysis |
| `POST`   | `/api/analyze/bulk`                  | Many resumes × one JD → ranked results |
| `GET`    | `/api/analyze/history`               | Get user's analysis history            |
| `DELETE` | `/api/analyze/history/{analysis_id}` | Delete one analysis                    |
| `POST`   | `/api/analyze/history/delete`        | Bulk-delete or delete all              |
| `GET`    | `/api/analyze/{analysis_id}/report`  | Download PDF report                    |

---

### Optional AI Endpoints

| Path                          | Returns                           |
| ----------------------------- | --------------------------------- |
| `/api/ai/status`              | AI capability status              |
| `/api/ai/features`            | Available AI features             |
| `/api/ai/cover-letter`        | Tailored cover letter             |
| `/api/ai/interview-questions` | Interview questions               |
| `/api/ai/resume-strength`     | AI-based resume strength analysis |
| `/api/ai/improvements`        | Targeted improvement suggestions  |
| `/api/ai/predict-roles`       | AI-based role predictions         |
| `/api/ai/semantic-match`      | Embedding-based skill matching    |

---

## Pipeline Flow

```text
POST /api/analyze
(multipart: resume_file + jd_text | jd_file)
        │
        ▼
parse_resume()
PDF/DOCX → structured resume data
        │
        ▼
process_job_description()
JD text/file → skills + keywords
        │
        ▼
pipeline.run_full_analysis()
        │
        ├── Match Score
        │
        ├── ATS Score
        │
        ├── Role Prediction
        │
        ├── Recommendations
        │
        └── Verdict
        │
        ▼
Persist results in MongoDB
        │
        ▼
AnalysisResponse
        │
        ▼
Frontend Result Dashboard
```

---

## ATS Scoring

The ATS score is calculated using four weighted components:

| Component  | Weight |
| ---------- | -----: |
| Keywords   |    45% |
| Skills     |    25% |
| Sections   |    15% |
| Experience |    15% |

The final result includes a breakdown of the different scoring components.

---

## MongoDB Collections

The application uses MongoDB Atlas for persistent storage.

### `users`

Stores authentication records.

* Unique index on `email`

### `user_profiles`

Stores the user's persistent profile and parsed resume information.

### `resumes`

Stores uploaded resumes and parsed `resume_data`.

### `job_descriptions`

Stores job descriptions and parsed `jd_data`.

### `analysis_results`

Stores analysis snapshots including:

* Scores
* Missing skills
* Recommendations
* Predicted roles
* Verdict

### `password_resets`

Stores active OTP reset sessions.

Password-reset entries use a TTL index so expired reset sessions can be automatically removed.

Indexes are ensured during application startup.

---

## Security

| Control                                                           | Location                             |
| ----------------------------------------------------------------- | ------------------------------------ |
| **JWT authentication** with environment-driven secret             | `backend/routers/auth_routes.py`     |
| **bcrypt password hashing**                                       | `auth_routes.py`                     |
| **Rate limiting** using a sliding window                          | `backend/utils/rate_limit.py`        |
| **OTP password reset** with TTL, max attempts and resend cooldown | `auth_routes.py`, `email_service.py` |
| **Security headers**                                              | `backend/main.py`                    |
| **Trusted hosts + environment-driven CORS**                       | `backend/main.py`                    |
| **Request IDs in error responses**                                | `backend/main.py`                    |
| **Production error protection**                                   | `backend/main.py`                    |
| **Configurable upload size limit**                                | Environment configuration            |
| **Automatic logout on invalid/stale JWT**                         | `frontend/src/services/api.js`       |

---

## Production Deployment Checklist

Before deploying the application to production:

1. Set `JWT_SECRET_KEY` to a long, random secret.
2. Set:

```text
APP_ENV=production
```

3. Configure:

```text
MONGODB_REQUIRED=true
```

4. Restrict:

```text
CORS_ALLOWED_ORIGINS
TRUSTED_HOSTS
```

to the actual production domains.

5. Only enable:

```text
TRUST_PROXY_HEADERS=true
```

when running behind a trusted reverse proxy.

6. Keep all API keys, database credentials, SMTP credentials and JWT secrets outside the source code.

---

## Deployment

### Live Demo

https://ai-resume-analyzer-frontend-px1q.onrender.com

### Backend

The backend can be deployed to platforms that support Python applications, such as:

* Render
* Railway
* Fly.io
* Other Python-capable hosting platforms

For production deployments, use an appropriate ASGI server configuration such as Gunicorn with Uvicorn workers.

### Frontend

Build the frontend with:

```bash
npm run build
```

The generated:

```text
frontend/build/
```

directory can be deployed to a static hosting provider.

Set:

```text
REACT_APP_API_BASE_URL
```

to the production backend URL during the frontend build.

### Database

MongoDB Atlas is used as the application's database.

---

## Testing

The repository currently does **not** include a dedicated automated test suite or a `tests/` directory.

Testing can currently be performed manually by running the backend and frontend locally.

### Backend Testing

Start the backend:

```bash
uvicorn backend.main:app --reload
```

Verify that:

* The API starts successfully.
* `/health` responds correctly.
* User registration works.
* User login works.
* Resume upload works.
* Job description submission works.
* Resume analysis completes successfully.
* Analysis history can be retrieved.
* PDF reports can be downloaded.

### Frontend Testing

Start the frontend:

```bash
cd frontend
npm start
```

Verify that:

* The application loads successfully.
* Registration and login work.
* Resume upload works.
* Job descriptions can be submitted.
* Analysis results are displayed correctly.
* Analysis history can be viewed.
* PDF reports can be downloaded.

> Automated unit, integration, and end-to-end tests can be added in a future update.

---

## Roadmap

* [ ] Add unit-test coverage for `pipeline.run_full_analysis`
* [ ] Add integration tests for API endpoints
* [ ] Add end-to-end tests for the upload → analyze → download workflow
* [ ] Containerized deployment with Docker
* [ ] Migration from Create React App to Vite
* [ ] Redis-backed rate limiter for multi-worker deployments
* [ ] Add subscription/billing functionality for premium AI features

---

## License

[MIT](LICENSE) © 2026 ResuMatch AI
