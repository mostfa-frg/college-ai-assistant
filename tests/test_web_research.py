from unittest.mock import patch

from college_assistant.web_research import search_web_evidence


def test_web_research_is_disabled_without_key(monkeypatch):
    monkeypatch.setattr("college_assistant.web_research.TAVILY_API_KEY", None)
    with patch("college_assistant.web_research.urlopen") as urlopen:
        assert search_web_evidence("embedded systems GPIO") == []
        urlopen.assert_not_called()


def test_web_research_returns_only_results_with_title_url_and_snippet(monkeypatch):
    from io import BytesIO

    monkeypatch.setattr("college_assistant.web_research.TAVILY_API_KEY", "test-key")
    monkeypatch.setattr("college_assistant.web_research.WEB_RESEARCH_ENABLED", True)

    response_payload = {
        "results": [
            {"title": "Official docs", "url": "https://docs.example.test/topic", "content": "Relevant technical detail."},
            {"title": "No URL", "url": "javascript:alert(1)", "content": "Must be ignored."},
            {"title": "No content", "url": "https://example.test", "content": ""},
        ]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            import json
            return json.dumps(response_payload).encode("utf-8")

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://api.tavily.com/search"
        assert timeout == 12
        return FakeResponse()

    monkeypatch.setattr("college_assistant.web_research.urlopen", fake_urlopen)
    results = search_web_evidence("embedded systems GPIO")

    assert len(results) == 1
    assert results[0].source == "Official docs"
    assert results[0].location == "https://docs.example.test/topic"
    assert "Relevant technical detail" in results[0].text


def test_web_research_returns_empty_on_service_error(monkeypatch):
    from urllib.error import URLError

    monkeypatch.setattr("college_assistant.web_research.TAVILY_API_KEY", "test-key")
    monkeypatch.setattr("college_assistant.web_research.WEB_RESEARCH_ENABLED", True)

    def fail(*args, **kwargs):
        raise URLError("temporary failure")

    monkeypatch.setattr("college_assistant.web_research.urlopen", fail)
    assert search_web_evidence("embedded systems") == []
