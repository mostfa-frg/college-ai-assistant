from college_assistant import retrieval


def test_retrieval_is_scoped_to_course_material_folder(monkeypatch, tmp_path):
    materials = tmp_path / "materials"
    target_course = materials / "embedded_systems"
    other_course = materials / "distributed_systems"
    target_course.mkdir(parents=True)
    other_course.mkdir(parents=True)
    (target_course / "lecture_02.txt").write_text(
        "GPIO pins have electrical voltage limits. Verify the official board pinout before wiring.",
        encoding="utf-8",
    )
    (other_course / "lecture.txt").write_text(
        "Distributed systems coordinate replicas and consensus protocols.",
        encoding="utf-8",
    )
    monkeypatch.setattr(retrieval, "MATERIALS_DIR", materials)
    monkeypatch.setattr(retrieval, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(retrieval, "list_materials", lambda course_id: [])

    results = retrieval.retrieve_course_evidence("1327", "GPIO voltage pinout wiring", top_k=3)

    assert results
    assert results[0].source == "lecture_02.txt"
    assert "GPIO pins" in results[0].text
    assert all("distributed" not in result.source.casefold() for result in results)


def test_retrieval_returns_no_evidence_when_course_has_no_materials(monkeypatch, tmp_path):
    monkeypatch.setattr(retrieval, "MATERIALS_DIR", tmp_path / "materials")
    monkeypatch.setattr(retrieval, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(retrieval, "list_materials", lambda course_id: [])

    assert retrieval.retrieve_course_evidence("1327", "GPIO voltage pinout") == []


def test_retrieval_reads_word_materials(monkeypatch, tmp_path):
    from docx import Document

    materials = tmp_path / "materials"
    target_course = materials / "embedded_systems"
    target_course.mkdir(parents=True)
    word_path = target_course / "lecture.docx"
    document = Document()
    document.add_paragraph("SSH provides secure command-line access to an embedded Linux target.")
    document.save(word_path)

    monkeypatch.setattr(retrieval, "MATERIALS_DIR", materials)
    monkeypatch.setattr(retrieval, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(retrieval, "list_materials", lambda course_id: [])

    results = retrieval.retrieve_course_evidence("1327", "SSH command-line access", top_k=2)

    assert results
    assert "SSH provides secure command-line access" in results[0].text
    assert results[0].source == "lecture.docx"
