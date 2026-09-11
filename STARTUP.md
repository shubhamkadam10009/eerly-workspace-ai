# Startup Guide

This guide explains how to run the Eerly Workspace AI project locally from a fresh clone.

> **Security:** Never commit your `.env` file, Gemini API key, JWT secret, or a JWT bearer token to GitHub. Use your own credentials/tokens when running the application.

## 1. Clone the repository

```powershell
git clone https://github.com/shubhamkadam10009/eerly-workspace-ai.git
cd eerly-workspace-ai
```

## 2. Create the environment file

```powershell
Copy-Item .env.example .env
notepad .env
```

Set at least:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
JWT_SECRET=YOUR_RANDOM_SECRET_AT_LEAST_32_BYTES
```

Keep `.env` private. It is intentionally excluded by `.gitignore`.

## 3. Start the backend and PostgreSQL

```powershell
docker compose up --build
```

This starts PostgreSQL, FastAPI/Uvicorn, automatic Alembic migrations, and health checks.

API:
```text
http://localhost:8000
```

Health:
```text
http://localhost:8000/health
```

API docs:
```text
http://localhost:8000/docs
```

Keep this terminal running.

## 4. Start the Streamlit frontend

Open a **second PowerShell terminal**:

```powershell
cd C:\Users\<YOUR_WINDOWS_USERNAME>\Desktop\eerly-workspace-ai
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
streamlit run frontend/app.py
```

Frontend:

```text
http://localhost:8501
```

## 5. Authentication

The frontend requires a JWT bearer token.

**Do not commit a JWT token to this repository.** Generate a token using the same `JWT_SECRET` configured in `.env`.

After activating `.venv`, you can generate a local development token with:

```powershell
python -c "import jwt; print(jwt.encode({'sub':'user_b'}, 'YOUR_JWT_SECRET', algorithm='HS256'))"
```

Replace `YOUR_JWT_SECRET` with the exact value from `.env`.

Enter the generated token into the frontend's JWT/token field.

Example JWT payload:

```json
{
  "sub": "user_b"
}
```

The `sub` claim identifies the workspace user. The backend validates the token using the configured `JWT_SECRET`.

## 6. Application flow

```text
Streamlit :8501
      |
      v
FastAPI :8000
      |
      v
LangGraph
   |       |       |
 Gemini PostgreSQL Workspace
```

The workflow can analyze requests, discover/load skills, inspect and read workspace files, generate and validate output, pause for human approval, resume after approval/edit/rejection, and deliver artifacts.

## 7. Stop the application

Stop the foreground Docker process with:

```text
Ctrl+C
```

Or:

```powershell
docker compose down
```

This stops the containers while preserving the named PostgreSQL volume.

## 8. Remove the database volume

For a completely fresh database:

```powershell
docker compose down -v
```

This removes the PostgreSQL volume and its persisted data.

## Quick Start

After cloning:

```powershell
cd eerly-workspace-ai
Copy-Item .env.example .env
notepad .env
docker compose up --build
```

Then in a second terminal:

```powershell
cd C:\Users\<YOUR_WINDOWS_USERNAME>\Desktop\eerly-workspace-ai
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
streamlit run frontend/app.py
```

Open:

```text
http://localhost:8501
```

Generate a JWT using the same `JWT_SECRET` in `.env` and enter it in the frontend.
