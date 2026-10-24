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


def test_shared_catalog_loads_immutable_validated_presets_once(tmp_path, monkeypatch):
    from puzzle_common import catalog

    (tmp_path / "puzzles.json").write_text('{"쉬움": [[1]]}', encoding="utf-8")
    monkeypatch.setattr(catalog.resources, "files", lambda _: tmp_path)

    def validate(grid):
        return tuple(tuple(row) for row in grid)

    presets = catalog.load_catalog("cached_package", validate)
    assert presets == {"쉬움": ((1,),)}
    with pytest.raises(TypeError):
        presets["보통"] = ((2,),)
    (tmp_path / "puzzles.json").unlink()
    assert catalog.load_catalog("cached_package", validate) is presets


@pytest.mark.parametrize("content", ["[]", "{}", '{" ": [[1]]}', '{"쉬움": 0}'])
def test_shared_catalog_rejects_schema_and_puzzle_failures(
    tmp_path, monkeypatch, content
):
    from puzzle_common import catalog

    (tmp_path / "puzzles.json").write_text(content, encoding="utf-8")
    monkeypatch.setattr(catalog.resources, "files", lambda _: tmp_path)

    def validate(grid):
        raise ValueError("잘못된 영역 맵")

    with pytest.raises(catalog.PuzzleDataError):
        catalog.load_catalog("invalid_package", validate)
