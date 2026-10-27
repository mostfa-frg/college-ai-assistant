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



def test_regeneration_allows_recovery_when_approved_file_is_missing(monkeypatch, tmp_path):
    from pathlib import Path
    from college_assistant.storage import repositories
    from college_assistant.assignment_solutions import regenerate_assignment_draft
    import pytest

    monkeypatch.setattr(repositories, "get_assignment", lambda assignment_id: {
        "id": assignment_id,
        "title": "Approved but deleted assignment",
        "course_id": "1327",
        "url": "https://example.test/assignment",
        "submission_status": "not_submitted",
        "solution_status": "approved",
        "approved_solution_path": str(tmp_path / "deleted_approved.md"),
        "instructions_text": "Explain what an embedded system is and give an example.",
    })
    monkeypatch.setattr("college_assistant.assignment_solutions.SOLUTIONS_DIR", tmp_path)
    monkeypatch.setattr("college_assistant.assignment_solutions.LLM_API_KEY", "test-key")
    monkeypatch.setattr("college_assistant.assignment_solutions.LLM_MODEL", "test-model")

    class FakeCompletions:
        def create(self, **kwargs):
            class Message:
                content = "An embedded system is a computer designed for a specific function."
            class Choice:
                message = Message()
            class Response:
                choices = [Choice()]
            return Response()

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr("college_assistant.assignment_solutions.OpenAI", FakeClient)
    monkeypatch.setattr(repositories, "save_solution_draft", lambda assignment_id, path: None)

    result = regenerate_assignment_draft(assignment_id=9)
    assert result["path"].endswith("_v2.docx")
    assert Path(result["path"]).is_file()
    assert Path(result["word_path"]).is_file()


def test_regeneration_still_refuses_when_approved_file_exists(monkeypatch, tmp_path):
    from college_assistant.storage import repositories
    from college_assistant.assignment_solutions import regenerate_assignment_draft
    import pytest

    approved = tmp_path / "approved.docx"
    approved.write_text("approved content", encoding="utf-8")
    monkeypatch.setattr(repositories, "get_assignment", lambda assignment_id: {
        "id": assignment_id,
        "title": "Still approved",
        "submission_status": "not_submitted",
        "solution_status": "approved",
        "approved_solution_path": str(approved),
        "instructions_text": "Enough instructions to be considered valid.",
    })
    with pytest.raises(ValueError, match="approved solution file"):
        regenerate_assignment_draft(10)



def test_instruction_chunks_stay_within_limit_and_preserve_text():
    from college_assistant.assignment_solutions import _split_instruction_chunks

    source = ("\n\n".join(["A" * 2000, "B" * 2000, "C" * 2000]))
    chunks = _split_instruction_chunks(source, max_chars=2500)
    assert len(chunks) >= 3
    assert all(len(chunk) <= 2500 for chunk in chunks)
    assert "".join(chunks).replace("\n\n", "") == "A" * 2000 + "B" * 2000 + "C" * 2000



def test_instruction_chunks_keep_scenarios_and_subquestions_together():
    from college_assistant.assignment_solutions import _split_instruction_chunks

    source = (
        "Part A - Essay Questions\n"
        "1. Explain the host and target.\n"
        "2. Explain safe setup.\n"
        "Part B - MCQs\n"
        "1. Which remote method is best?\n"
        "Scenario 1 - Safe Setup\n"
        "1. What should be checked first?\n"
        "2. Explain the boot sequence.\n"
        "Scenario 2 - Network Failure\n"
        "1. Which checkpoint should be investigated?"
    )
    chunks = _split_instruction_chunks(source, max_chars=1000)

    scenario_one_chunks = [chunk for chunk in chunks if "Scenario 1 - Safe Setup" in chunk]
    assert len(scenario_one_chunks) == 1
    assert "1. What should be checked first?" in scenario_one_chunks[0]
    assert "2. Explain the boot sequence." in scenario_one_chunks[0]
    assert "Scenario 2 - Network Failure" in chunks[-1]


def test_prompt_requires_explicit_mcq_and_true_false_answers():
    from college_assistant.assignment_solutions import SYSTEM_PROMPT

    prompt = SYSTEM_PROMPT.casefold()
    assert "give the best answer explicitly" in prompt
    assert "begin the answer with exactly **true** or **false**" in prompt
    assert "never use missing evidence as a reason to leave a solvable question unanswered" in prompt


def test_sanitizes_citations_that_do_not_match_retrieved_files():
    from types import SimpleNamespace
    from college_assistant.assignment_solutions import _sanitize_citations

    evidence = [SimpleNamespace(source="lecture_02.pdf")]
    answer = (
        "SSH is used for command-line access [Source: lecture_02.pdf, page 4]. "
        "This citation is fake [Source: course_material_evidence]."
    )

    sanitized = _sanitize_citations(answer, evidence)

    assert "[Source: lecture_02.pdf, page 4]" in sanitized
    assert "[Source: course_material_evidence]" not in sanitized
    assert "no matching course source retrieved" in sanitized


def test_retrieves_course_evidence_separately_for_numbered_questions(monkeypatch):
    from types import SimpleNamespace
    from college_assistant import assignment_solutions

    queries = []

    def fake_retrieve(course_id, query, top_k):
        queries.append(query)
        return [SimpleNamespace(source="lecture.pdf", location="page 1", text=query[:100])]

    monkeypatch.setattr(assignment_solutions, "retrieve_course_evidence", fake_retrieve)
    evidence = assignment_solutions._retrieve_chunk_evidence(
        "1327",
        "ES-101",
        "Part A - Essay Questions\n1. Explain SSH.\n2. Explain Samba."
    )

    assert len(queries) == 2
    assert "Explain SSH" in queries[0]
    assert "Explain Samba" in queries[1]
    assert evidence


def test_task_chunks_preserve_all_numbered_questions_and_section_context():
    from college_assistant.assignment_solutions import _split_task_chunks

    source = (
        "Part A - Essay Questions\n"
        "1. Explain the host and target.\n"
        "A detailed answer prompt.\n"
        "2. Explain safe setup.\n"
        "Part B - MCQs\n"
        "1. Which method is best?\n"
        "A. SSH\nB. VNC\nC. Samba\n"
        "Scenario 1 - Safe Setup\n"
        "1. What should be checked first?\n"
        "2. Explain the boot sequence."
    )
    chunks = _split_task_chunks(source, max_chars=180)
    joined = "\n".join(chunks)

    assert "Part A - Essay Questions" in joined
    assert "Part B - MCQs" in joined
    assert "Scenario 1 - Safe Setup" in joined
    assert "Explain the host and target." in joined
    assert "Explain safe setup." in joined
    assert "Which method is best?" in joined
    assert "What should be checked first?" in joined
    assert "Explain the boot sequence." in joined
    assert all(len(chunk) <= 180 for chunk in chunks)


def test_word_export_does_not_use_auto_numbering_for_question_lines(tmp_path):
    from docx import Document
    from college_assistant.assignment_solutions import _write_word_document

    markdown = tmp_path / "numbering.md"
    markdown.write_text(
        "# Draft\n\n## Part A\n\n1. First question\n\n"
        "2. Second question\n\n## Part B\n\n1. First MCQ\n",
        encoding="utf-8",
    )
    word_path = _write_word_document(markdown)
    document = Document(word_path)
    numbered = [p for p in document.paragraphs if p.text[:1].isdigit()]

    assert [p.text for p in numbered] == [
        "1. First question", "2. Second question", "1. First MCQ"
    ]
    assert all(p.style.name != "List Number" for p in numbered)
