from fastapi import FastAPI, Query

from ai_dev_team import run_project

app = FastAPI(title="AI Dev Team")


@app.post("/run")
def run(idea: str = Query(..., min_length=1)) -> dict:
    return run_project(idea=idea)
