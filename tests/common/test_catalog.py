import pytest


def test_shared_catalog_reader_preserves_unicode(tmp_path, monkeypatch):
    from puzzle_common import catalog

    (tmp_path / "puzzles.json").write_text('{"쉬움": [[1]]}', encoding="utf-8")
    monkeypatch.setattr(catalog.resources, "files", lambda _: tmp_path)

    assert catalog.read_catalog("any_package") == {"쉬움": [[1]]}


@pytest.mark.parametrize("content", [None, "{broken"])
def test_shared_catalog_reader_reports_file_and_json_failures(
    tmp_path, monkeypatch, content
):
    from puzzle_common import catalog

    if content is not None:
        (tmp_path / "puzzles.json").write_text(content, encoding="utf-8")
    monkeypatch.setattr(catalog.resources, "files", lambda _: tmp_path)

    with pytest.raises(catalog.PuzzleDataError, match="puzzles.json"):
        catalog.read_catalog("any_package")
