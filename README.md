# AI Dev Team

Multi-agent software delivery orchestrator that turns an idea into iterative code, tests, QA findings, and architecture review inside a git-tracked `workspace/`.

## What This Project Provides

- Installable Python package (`pip install -e .`).
- Public API: `from ai_dev_team import run_project`.
- CLI entrypoint: `ai-dev-team --idea "..."`
- FastAPI endpoint: `POST /run?idea=...`
- Generated artifacts and commits under `workspace/`.

## Prerequisites

- Python 3.10+
- Git installed and available on `PATH`
- OpenAI API key

## Setup

1) Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies and package in editable mode:

```bash
pip install -r requirements.txt
pip install -e .
```

3) Configure environment:

```bash
cp .env.example .env
```

Set at minimum:

```env
OPENAI_API_KEY=your_real_key
```

Optional settings:

- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `MAX_ITERATIONS` (default: `5`)
- `EXEC_TIMEOUT_SECONDS` (default: `15`)
- `PYTEST_TIMEOUT_SECONDS` (default: `20`)
- `WORKSPACE_PATH` (default: `workspace`)

## Run From CLI

```bash
ai-dev-team --idea "Build a simple notes API with CRUD and tests"
```

Expected response shape:

```json
{
  "status": "success | partial_success | failed",
  "iterations": 3,
  "score": 82,
  "summary": "Completed X/Y tasks across Z iterations.",
  "artifacts": {
    "workspace_path": "workspace",
    "memory": {}
  }
}
```

## Run As API

Start server:

```bash
uvicorn ai_dev_team.app.main:app --host 127.0.0.1 --port 8000
```

Example request:

```bash
curl -X POST "http://127.0.0.1:8000/run?idea=Build%20a%20simple%20notes%20API"
```

Equivalent PowerShell request:

```powershell
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/run?idea=Build%20a%20simple%20notes%20API"
```

## Public Package API

```python
from ai_dev_team import run_project

result = run_project("Build a simple notes API")
print(result["status"], result["score"])
```

## Expected Artifacts In `workspace/`

After one or more runs, you should see:

- `workspace/main.py`
- `workspace/services/`
- `workspace/models/`
- `workspace/utils/`
- `workspace/tests/`
- `workspace/.git/` with iteration commits

Commit messages are generated per iteration, for example:

- `task:<id> iteration:<n> engineer changes`
- `task:<id> iteration:<n> generated tests`

## Smoke Test Flow (Local)

Use this quick end-to-end check:

1. Activate virtual environment
2. `pip install -r requirements.txt && pip install -e .`
3. Set `OPENAI_API_KEY` in `.env`
4. Run:
   - CLI: `ai-dev-team --idea "Build a tiny calculator app"`
   - API: `uvicorn ai_dev_team.app.main:app` and `POST /run?idea=...`
5. Verify:
   - JSON response includes `status`, `iterations`, `score`, `summary`
   - Files/dirs exist under `workspace/`
   - `workspace/` contains git commits

## Troubleshooting

- `Python was not found` on Windows:
  - Install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/)
  - Re-open terminal and retry `python --version`
- OpenAI auth/config errors:
  - Confirm `.env` exists and `OPENAI_API_KEY` is valid
- Git commit errors:
  - Configure local git identity:
    - `git config --global user.name "Your Name"`
    - `git config --global user.email "you@example.com"`
