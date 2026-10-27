from college_assistant.portal_sync import _activity_key, _activity_type


def test_activity_key_uses_moodle_activity_id():
    assert _activity_key(
        "https://learn3.sha.edu.eg/mod/assign/view.php?id=6069&action=editsubmission"
    ) == "/mod/assign/view.php?id=6069"


def test_activity_key_preserves_query_without_id():
    assert _activity_key(
        "https://learn3.sha.edu.eg/mod/page/view.php?foo=bar"
    ) == "/mod/page/view.php?foo=bar"


def test_activity_type_classifies_common_moodle_modules():
    assert _activity_type("https://learn3.sha.edu.eg/mod/assign/view.php?id=1") == "assignment"
    assert _activity_type("https://learn3.sha.edu.eg/mod/resource/view.php?id=2") == "material"
    assert _activity_type("https://learn3.sha.edu.eg/mod/folder/view.php?id=3") == "material"
    assert _activity_type("https://learn3.sha.edu.eg/mod/forum/view.php?id=4") == "announcement_or_forum"


class _FakeElement:
    def __init__(self, text="", href=None):
        self._text = text
        self._href = href

    def inner_text(self, timeout=None):
        return self._text

    def get_attribute(self, name):
        return self._href if name == "href" else None


class _FakeLocator:
    def __init__(self, elements=()):
        self.elements = list(elements)

    def count(self):
        return len(self.elements)

    def nth(self, index):
        return self.elements[index]


class _FakePage:
    def __init__(self, selectors):
        self.selectors = selectors

    def locator(self, selector):
        return _FakeLocator(self.selectors.get(selector, []))


def test_assignment_extraction_uses_description_not_entire_page():
    from college_assistant.portal_sync import _extract_assignment_instructions

    page = _FakePage({
        "#intro": [_FakeElement("Answer the following three questions.")],
        ".activity-description": [_FakeElement("Answer the following three questions.")],
    })

    content = _extract_assignment_instructions(page)

    assert "Answer the following three questions." in content
    assert "ATTACHMENT_FILES_DETECTED_NOT_EXTRACTED" not in content
    assert "ASSIGNMENT_DESCRIPTION_NOT_FOUND" not in content


def test_assignment_extraction_flags_unread_attachments():
    from college_assistant.portal_sync import _extract_assignment_instructions

    page = _FakePage({
        ".assignsubmission_file a": [_FakeElement("assignment.pdf", "/pluginfile.php/123/assignment.pdf")],
    })

    content = _extract_assignment_instructions(page)

    assert "ATTACHMENT_FILES_DETECTED_NOT_EXTRACTED" in content
    assert "assignment.pdf" in content


def test_assignment_extraction_flags_missing_description():
    from college_assistant.portal_sync import _extract_assignment_instructions

    content = _extract_assignment_instructions(_FakePage({}))

    assert "ASSIGNMENT_DESCRIPTION_NOT_FOUND" in content


class _FakeElement:
    def __init__(self, text="", href=None):
        self._text = text
        self._href = href

    def inner_text(self, timeout=None):
        return self._text

    def get_attribute(self, name):
        return self._href if name == "href" else None


class _FakeLocator:
    def __init__(self, elements=()):
        self.elements = list(elements)

    def count(self):
        return len(self.elements)

    def nth(self, index):
        return self.elements[index]


class _FakePage:
    def __init__(self, selectors):
        self.selectors = selectors

    def locator(self, selector):
        return _FakeLocator(self.selectors.get(selector, []))


def test_assignment_extraction_uses_description_not_entire_page():
    from college_assistant.portal_sync import _extract_assignment_instructions

    page = _FakePage({
        "#intro": [_FakeElement("Answer the following three questions.")],
        ".activity-description": [_FakeElement("Answer the following three questions.")],
    })

    content = _extract_assignment_instructions(page)

    assert "Answer the following three questions." in content
    assert "ATTACHMENT_FILES_DETECTED_NOT_EXTRACTED" not in content
    assert "ASSIGNMENT_DESCRIPTION_NOT_FOUND" not in content


def test_assignment_extraction_flags_unread_attachments():
    from college_assistant.portal_sync import _extract_assignment_instructions

    page = _FakePage({
        ".assignsubmission_file a": [_FakeElement("assignment.pdf", "/pluginfile.php/123/assignment.pdf")],
    })

    content = _extract_assignment_instructions(page)

    assert "ATTACHMENT_FILES_DETECTED_NOT_EXTRACTED" in content
    assert "assignment.pdf" in content


def test_assignment_extraction_flags_missing_description():
    from college_assistant.portal_sync import _extract_assignment_instructions

    content = _extract_assignment_instructions(_FakePage({}))

    assert "ASSIGNMENT_DESCRIPTION_NOT_FOUND" in content



def test_pdf_attachment_text_is_extracted_with_authenticated_context():
    import fitz
    from college_assistant.portal_sync import _extract_pdf_text

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "ES-101 Assignment: Explain the boot sequence and GPIO voltage safety.")
    payload = document.tobytes()
    document.close()

    class Response:
        ok = True
        def body(self):
            return payload

    class Request:
        def get(self, url, timeout=None):
            assert url == "https://learn3.sha.edu.eg/pluginfile.php/123/assignment.pdf"
            return Response()

    class Context:
        request = Request()

    class Page:
        url = "https://learn3.sha.edu.eg/mod/assign/view.php?id=1"
        context = Context()

    extracted = _extract_pdf_text(Page(), "/pluginfile.php/123/assignment.pdf")
    assert extracted is not None
    assert "boot sequence" in extracted
    assert "GPIO voltage safety" in extracted


def test_pdf_attachment_without_text_returns_ocr_sentinel():
    import fitz
    from college_assistant.portal_sync import _extract_pdf_text

    document = fitz.open()
    document.new_page()
    payload = document.tobytes()
    document.close()

    class Response:
        ok = True
        def body(self):
            return payload

    class Request:
        def get(self, url, timeout=None):
            return Response()

    class Context:
        request = Request()

    class Page:
        url = "https://learn3.sha.edu.eg/mod/assign/view.php?id=1"
        context = Context()

    assert _extract_pdf_text(Page(), "/pluginfile.php/123/scanned.pdf") == "PDF_TEXT_EXTRACTION_EMPTY_OCR_REQUIRED"
