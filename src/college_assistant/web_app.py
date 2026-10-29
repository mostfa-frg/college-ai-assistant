from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from college_assistant.assignment_solutions import regenerate_assignment_draft
from college_assistant.config import PORTAL_STATE_FILE, SOLUTIONS_DIR
from college_assistant.portal_login import save_portal_login_from_web
from college_assistant.portal_sync import run_sync
from college_assistant.storage.database import initialize_database
from college_assistant.storage.repositories import (
    approve_solution,
    get_assignment,
    list_assignments,
)

app = FastAPI(title="College AI Assistant", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    assignments = list_assignments()
    counts = {
        "total": len(assignments),
        "ready": sum(a.get("submission_status") == "not_submitted" for a in assignments),
        "review": sum(a.get("solution_status") == "pending_review" for a in assignments),
        "approved": sum(a.get("solution_status") == "approved" for a in assignments),
    }
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"assignments": assignments, "counts": counts},
    )


@app.get("/api/assignments")
def assignments_api():
    """Return assignment metadata only; never expose local credentials or session state."""
    return {"assignments": list_assignments()}


@app.get("/api/assignments/{assignment_id}")
def assignment_api(assignment_id: int):
    assignment = get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"assignment": assignment}


@app.post("/actions/check")
def check_assignments():
    """Sync Moodle, recovering an absent or expired session through a visible login browser."""
    try:
        if not PORTAL_STATE_FILE.is_file():
            save_portal_login_from_web()
        try:
            run_sync()
        except RuntimeError as exc:
            if "portal session expired" not in str(exc).casefold():
                raise
            save_portal_login_from_web()
            run_sync()
    except (RuntimeError, FileNotFoundError, OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Moodle could not be refreshed. If a sign-in browser opened, complete "
                f"the login and try again. Details: {exc}"
            ),
        ) from exc
    return RedirectResponse(url="/?notice=check-complete", status_code=303)


@app.post("/actions/generate/{assignment_id}")
def generate_draft(assignment_id: int):
    assignment = get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.get("submission_status") != "not_submitted":
        raise HTTPException(
            status_code=409,
            detail="Draft generation is allowed only when Moodle explicitly reports not_submitted.",
        )
    try:
        regenerate_assignment_draft(assignment_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RedirectResponse(url="/?notice=draft-generated", status_code=303)


@app.post("/actions/approve/{assignment_id}")
def approve_draft(assignment_id: int):
    assignment = get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    draft = assignment.get("solution_path")
    if not draft or not Path(draft).is_file():
        raise HTTPException(status_code=409, detail="No saved draft file is available to review.")
    SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
    approved_path = (SOLUTIONS_DIR / f"assignment_{assignment_id}_approved.docx").resolve()
    solutions_root = SOLUTIONS_DIR.resolve()
    if approved_path.parent != solutions_root:
        raise HTTPException(status_code=400, detail="Invalid solution path")
    import shutil
    shutil.copy2(draft, approved_path)
    if not approve_solution(assignment_id, approved_path):
        raise HTTPException(status_code=409, detail="Local review status could not be saved.")
    return RedirectResponse(url="/?notice=marked-reviewed", status_code=303)


@app.get("/actions/open/{assignment_id}")
def open_draft(assignment_id: int):
    assignment = get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    raw_path = assignment.get("approved_solution_path") or assignment.get("solution_path")
    if not raw_path:
        raise HTTPException(status_code=404, detail="No saved draft exists")
    path = Path(raw_path).resolve()
    root = SOLUTIONS_DIR.resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Saved draft file was not found")
    return FileResponse(path, filename=path.name)
