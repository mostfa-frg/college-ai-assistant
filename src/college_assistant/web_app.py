from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from college_assistant.assignment_solutions import regenerate_assignment_draft
from college_assistant.config import LLM_MODEL, LLM_PROVIDER, PORTAL_STATE_FILE, SOLUTIONS_DIR
from college_assistant.portal_login import complete_portal_login_from_web, start_portal_login_from_web
from college_assistant.portal_sync import run_sync
from college_assistant.storage.database import initialize_database
from college_assistant.storage.repositories import (
    approve_solution,
    get_assignment,
    list_assignments,
    list_materials,
    list_courses,
)

app = FastAPI(title="College AI Assistant", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.on_event("startup")
def startup() -> None:
    initialize_database()


def _workspace_page(request: Request, active: str, title: str, subtitle: str, **extra):
    assignments = list_assignments()
    grouped = {}
    for item in assignments:
        grouped.setdefault(item.get("course_title") or item.get("course_id") or "Other", []).append(item)
    counts = {
        "total": len(assignments),
        "ready": sum(a.get("submission_status") == "not_submitted" for a in assignments),
        "review": sum(a.get("solution_status") == "pending_review" for a in assignments),
        "approved": sum(a.get("solution_status") == "approved" for a in assignments),
    }
    context = {
        "request": request, "active": active, "page_title": title,
        "section_label": "College AI Assistant / Workspace", "subtitle": subtitle,
        "assignments": assignments, "assignments_by_course": grouped, "counts": counts,
        "notice_text": "Moodle check completed. Assignment and course data has been refreshed."
            if request.query_params.get("notice") == "check-complete" else None,
    }
    context.update(extra)
    return templates.TemplateResponse(request=request, name="workspace.html", context=context)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return _workspace_page(request, "overview", "Overview",
        "A clear snapshot of assignments and the latest state of your coursework.")


@app.get("/assignments", response_class=HTMLResponse)
def assignments_page(request: Request, course_id: str | None = None):
    assignments = list_assignments()
    if course_id:
        assignments = [a for a in assignments if a.get("course_id") == course_id]
    grouped = {}
    for item in assignments:
        grouped.setdefault(item.get("course_title") or item.get("course_id") or "Other", []).append(item)
    return _workspace_page(request, "assignments", "Assignments",
        "Assignments grouped by course, ready for tracking and local review.",
        assignments=assignments, assignments_by_course=grouped)


@app.get("/courses", response_class=HTMLResponse)
def courses_page(request: Request):
    return _workspace_page(request, "courses", "Courses",
        "Your enrolled Moodle courses and their locally stored content.", courses=list_courses())


@app.get("/materials", response_class=HTMLResponse)
def materials_page(request: Request, course_id: str | None = None):
    return _workspace_page(request, "materials", "Materials",
        "Browse course files already downloaded to this computer.", materials=list_materials(course_id))


@app.get("/drafts", response_class=HTMLResponse)
def drafts_page(request: Request):
    drafts = [a for a in list_assignments() if a.get("solution_path") or a.get("approved_solution_path")]
    return _workspace_page(request, "drafts", "Drafts & Review",
        "Generated solutions and locally approved copies.", drafts=drafts)


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return _workspace_page(request, "settings", "Settings",
        "Connection and model information for this local installation.",
        session_exists=PORTAL_STATE_FILE.is_file(), provider=LLM_PROVIDER, model=LLM_MODEL)


@app.get("/materials/{material_id}")
def open_material(material_id: int):
    material = next((item for item in list_materials() if item["id"] == material_id), None)
    if not material or not material.get("file_path"):
        raise HTTPException(status_code=404, detail="Material file not found")
    path = Path(material["file_path"]).resolve()
    from college_assistant.config import MATERIALS_DIR
    root = MATERIALS_DIR.resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Material file is unavailable")
    return FileResponse(path, filename=path.name)

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
    """Sync Moodle; start a user-controlled sign-in flow when required."""
    if not PORTAL_STATE_FILE.is_file():
        try:
            start_portal_login_from_web()
        except Exception as exc:
            return RedirectResponse(url="/?error=" + quote("Could not open Moodle sign-in: " + str(exc), safe=""), status_code=303)
        return RedirectResponse(url="/?notice=login-opened", status_code=303)

    try:
        results = run_sync(download_materials=True)
    except RuntimeError as exc:
        if "portal session expired" not in str(exc).casefold():
            return RedirectResponse(url="/?error=" + quote("Moodle sync failed: " + str(exc), safe=""), status_code=303)
        try:
            PORTAL_STATE_FILE.unlink(missing_ok=True)
            start_portal_login_from_web()
        except Exception as login_exc:
            return RedirectResponse(url="/?error=" + quote("Session expired and sign-in could not start: " + str(login_exc), safe=""), status_code=303)
        return RedirectResponse(url="/?notice=login-opened", status_code=303)
    except (FileNotFoundError, OSError, TimeoutError) as exc:
        return RedirectResponse(url="/?error=" + quote("Moodle sync failed: " + str(exc), safe=""), status_code=303)
    change_count = sum(len(course.get("changes", [])) for course in results)
    return RedirectResponse(
        url=f"/?notice=check-complete&changes={change_count}",
        status_code=303,
    )


@app.post("/actions/login/complete")
def complete_login():
    """Verify/save SSO only after the user confirms they've finished signing in."""
    try:
        verified, detail = complete_portal_login_from_web()
        if not verified:
            return RedirectResponse(
                url="/?login_error=" + quote(detail, safe=""),
                status_code=303,
            )
        results = run_sync(download_materials=True)
    except (RuntimeError, FileNotFoundError, OSError, TimeoutError) as exc:
        return RedirectResponse(url="/?login_error=" + quote("Sign-in or Moodle sync failed: " + str(exc), safe=""), status_code=303)
    change_count = sum(len(course.get("changes", [])) for course in results)
    return RedirectResponse(
        url=f"/?notice=check-complete&changes={change_count}",
        status_code=303,
    )


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
    course_name = assignment.get("course_title") or f"course_{assignment['course_id']}"
    course_folder = re.sub(r"[^A-Za-z0-9_-]+", "_", course_name).strip("_")[:60] or "course"
    course_dir = (SOLUTIONS_DIR / course_folder).resolve()
    course_dir.mkdir(parents=True, exist_ok=True)
    approved_path = (course_dir / f"assignment_{assignment_id}_approved.docx").resolve()
    solutions_root = SOLUTIONS_DIR.resolve()
    if solutions_root not in approved_path.parents:
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
