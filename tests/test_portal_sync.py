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
