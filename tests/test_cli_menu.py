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
