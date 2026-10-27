from college_assistant.assignment_solutions import _is_placeholder_draft


def test_rejects_the_placeholder_template_from_the_current_assignment():
    draft = """
    Part A – Essay Questions
    1 | <Question 1> | Insert your essay here.
    Example placeholder: Brief explanation of why B is correct.
    """
    assert _is_placeholder_draft(draft)


def test_rejects_insufficient_assignment_content_marker():
    assert _is_placeholder_draft("INSUFFICIENT_ASSIGNMENT_CONTENT")


def test_accepts_a_substantive_answer_without_template_markers():
    draft = """
    ## Question 1: What is an embedded system?
    An embedded system is a computer designed to perform a specific function
    within a larger device. It commonly combines hardware and software.
    """
    assert not _is_placeholder_draft(draft)



def test_regeneration_refuses_assignments_not_explicitly_unsubmitted(monkeypatch):
    from college_assistant.storage import repositories
    from college_assistant.assignment_solutions import regenerate_assignment_draft

    monkeypatch.setattr(repositories, "get_assignment", lambda assignment_id: {
        "id": assignment_id,
        "title": "Submitted assignment",
        "submission_status": "submitted",
        "solution_status": "pending_review",
        "instructions_text": "Actual instructions with enough content.",
    })
    import pytest
    with pytest.raises(ValueError, match="not_submitted"):
        regenerate_assignment_draft(7)


def test_regeneration_refuses_incomplete_source(monkeypatch):
    from college_assistant.storage import repositories
    from college_assistant.assignment_solutions import regenerate_assignment_draft

    monkeypatch.setattr(repositories, "get_assignment", lambda assignment_id: {
        "id": assignment_id,
        "title": "Assignment with unreadable attachment",
        "submission_status": "not_submitted",
        "solution_status": "pending_review",
        "instructions_text": "ATTACHMENT_FILES_DETECTED_NOT_EXTRACTED " + ("x" * 40),
    })
    import pytest
    with pytest.raises(ValueError, match="incomplete or requires OCR"):
        regenerate_assignment_draft(8)


def test_prompt_requires_section_local_question_numbering_and_separate_answer_steps():
    from college_assistant.assignment_solutions import SYSTEM_PROMPT

    prompt = SYSTEM_PROMPT.casefold()
    assert "restarting at 1 for each section" in prompt
    assert "never number answer steps as additional questions" in prompt
    assert "keep scenario subquestions grouped" in prompt


def test_word_export_creates_docx_with_heading_and_lists(tmp_path):
    from docx import Document
    from college_assistant.assignment_solutions import _write_word_document

    markdown = tmp_path / "draft.md"
    markdown.write_text(
        "# Assignment draft\n\n## Part A\n\n"
        "**Question 1:** Explain the process.\n\n"
        "- First step\n- Second step\n",
        encoding="utf-8",
    )

    word_path = _write_word_document(markdown)

    assert word_path.exists()
    assert word_path.suffix == ".docx"
    document = Document(word_path)
    texts = [paragraph.text for paragraph in document.paragraphs]
    assert "Assignment draft" in texts
    assert "Part A" in texts
    assert any("Question 1:" in value for value in texts)
    assert any("First step" in value for value in texts)
