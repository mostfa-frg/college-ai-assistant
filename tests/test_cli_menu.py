def test_running_without_arguments_opens_menu_instead_of_sync(monkeypatch):
    from college_assistant import main as app_main

    calls = []
    monkeypatch.setattr("sys.argv", ["college-ai-assistant"])
    monkeypatch.setattr(app_main, "initialize_database", lambda: calls.append("init"))
    monkeypatch.setattr(app_main, "_interactive_menu", lambda: calls.append("menu"))
    monkeypatch.setattr(app_main, "run_sync", lambda: calls.append("sync"))

    app_main.main()

    assert calls == ["init", "menu"]


def test_menu_draft_list_only_includes_explicitly_unsubmitted(monkeypatch, capsys):
    from college_assistant import main as app_main

    monkeypatch.setattr(app_main, "list_assignments", lambda: [
        {"id": 1, "title": "Pending", "course_id": "1327", "submission_status": "not_submitted"},
        {"id": 2, "title": "Unknown", "course_id": "1327", "submission_status": "unknown"},
        {"id": 3, "title": "Submitted", "course_id": "1327", "submission_status": "submitted"},
    ])
    answers = iter(["2", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    app_main._generate_draft()
    output = capsys.readouterr().out

    assert "[1] Pending" in output
    assert "[2] Unknown" not in output
    assert "[3] Submitted" not in output

 

def test_assignment_check_does_not_generate_drafts_or_download_materials(monkeypatch, capsys):
    from college_assistant import main as app_main

    class PortalState:
        @staticmethod
        def is_file():
            return True

    monkeypatch.setattr(app_main, "PORTAL_STATE_FILE", PortalState())
    calls = []
    monkeypatch.setattr(app_main, "run_sync", lambda: calls.append("scan") or [])
    monkeypatch.setattr(app_main, "print_report", lambda results: calls.append("report"))
    monkeypatch.setattr(app_main, "list_assignments", lambda: [
        {"id": 1, "title": "Pending", "submission_status": "not_submitted"},
        {"id": 2, "title": "Unknown", "submission_status": "unknown"},
    ])
    app_main._check_assignments()
    assert calls == ["scan", "report"]
    assert "explicitly marked not submitted" in capsys.readouterr().out


def test_menu_shows_guided_workflow(monkeypatch, capsys):
    from college_assistant import main as app_main

    class PortalState:
        @staticmethod
        def is_file():
            return True

    monkeypatch.setattr(app_main, "PORTAL_STATE_FILE", PortalState())
    monkeypatch.setattr("builtins.input", lambda prompt="": "0")
    app_main._interactive_menu()
    output = capsys.readouterr().out
    assert "Check Moodle assignments" in output
    assert "Prepare an assignment draft" in output
    assert "Recommended workflow" in output
