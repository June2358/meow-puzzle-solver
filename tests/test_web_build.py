import shutil
import tomllib
from zipfile import ZipFile

import pytest

from scripts import build_web


def _configure_fake_project(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("import pygame\n", encoding="utf-8")
    for name in ("meow", "sudoku", "puzzle_common"):
        package = project / name
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "data.json").write_text("{}", encoding="utf-8")
    fonts = project / "puzzle_common/assets/fonts"
    fonts.mkdir(parents=True)
    for name in (
        "Pretendard-Regular.otf",
        "Pretendard-SemiBold.otf",
        "OFL-Pretendard.txt",
    ):
        (fonts / name).write_bytes(name.encode())
    monkeypatch.setattr(build_web, "PROJECT_ROOT", project)
    monkeypatch.setattr(build_web, "BUILD_ROOT", project / "build")
    monkeypatch.setattr(build_web, "WEB_OUTPUT", project / "build/web")
    return project


def test_staging_contains_both_puzzles_and_shared_assets_once(monkeypatch, tmp_path):
    project = _configure_fake_project(monkeypatch, tmp_path)
    for name in ("meow", "sudoku", "puzzle_common"):
        cache = project / name / "__pycache__"
        cache.mkdir()
        (cache / "module.pyc").write_bytes(b"cache")
        (project / name / "module.pyo").write_bytes(b"cache")
    stage = project / "build/puzzle-solvers"
    stage.mkdir(parents=True)
    (stage / "stale.py").write_text("old")
    sibling = project / "build/unrelated"
    sibling.mkdir()
    (sibling / "keep.txt").write_text("keep")

    assert build_web.stage_runtime_files() == stage
    files = {
        path.relative_to(stage).as_posix()
        for path in stage.rglob("*")
        if path.is_file()
    }
    assert files == {
        "main.py",
        "meow/__init__.py",
        "meow/data.json",
        "sudoku/__init__.py",
        "sudoku/data.json",
        "puzzle_common/__init__.py",
        "puzzle_common/data.json",
        "puzzle_common/assets/fonts/Pretendard-Regular.otf",
        "puzzle_common/assets/fonts/Pretendard-SemiBold.otf",
        "puzzle_common/assets/fonts/OFL-Pretendard.txt",
    }
    assert (stage / "main.py").read_bytes() == (project / "main.py").read_bytes()
    assert (sibling / "keep.txt").is_file()


@pytest.mark.parametrize("missing", ("main.py", "meow", "sudoku", "puzzle_common"))
def test_invalid_runtime_preserves_previous_stage(monkeypatch, tmp_path, missing):
    project = _configure_fake_project(monkeypatch, tmp_path)
    target = project / missing
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    stage = project / "build/puzzle-solvers"
    stage.mkdir(parents=True)
    (stage / "keep.txt").write_text("keep")
    with pytest.raises(FileNotFoundError):
        build_web.stage_runtime_files()
    assert (stage / "keep.txt").is_file()


def test_build_publishes_one_pyscript_bundle_with_compatibility_redirects(
    monkeypatch, tmp_path
):
    project = _configure_fake_project(monkeypatch, tmp_path)
    web = project / "build/web"
    web.mkdir(parents=True)
    (web / "stale.txt").write_text("stale")
    cache = project / "meow/__pycache__"
    cache.mkdir()
    (cache / "module.pyc").write_bytes(b"cache")
    (project / "secret.txt").write_text("not runtime")

    build_web.build_web()

    assert {
        path.relative_to(web).as_posix() for path in web.rglob("*") if path.is_file()
    } == {
        "index.html",
        "pyscript.toml",
        "runtime.zip",
        "meow/index.html",
        "sudoku/index.html",
        "pyscript/index.html",
    }
    with ZipFile(web / "runtime.zip") as archive:
        names = set(archive.namelist())
        assert "meow/data.json" in names and "sudoku/data.json" in names
        font = "puzzle_common/assets/fonts/Pretendard-Regular.otf"
        assert archive.read(font) == (project / font).read_bytes()
        assert "main.py" in names
        assert not any("__pycache__" in name or "secret.txt" in name for name in names)
        assert all(not name.startswith("/") and "\\" not in name for name in names)
    config = tomllib.loads((web / "pyscript.toml").read_text(encoding="utf-8"))
    assert config["files"] == {"./runtime.zip": "./*"}
    html = (web / "index.html").read_text(encoding="utf-8")
    assert "https://pyscript.net/releases/2026.7.3/core.js" in html
    assert 'id="canvas"' in html and 'type="py-game"' in html
    assert 'config="pyscript.toml"' in html and "await run_app()" in html
    for key in ("meow", "sudoku"):
        redirect = (web / key / "index.html").read_text(encoding="utf-8")
        assert f"url=../?puzzle={key}" in redirect
        assert f'href="../?puzzle={key}"' in redirect
    legacy = (web / "pyscript/index.html").read_text(encoding="utf-8")
    assert 'location.replace("../" + location.search)' in legacy
    assert 'href="../"' in legacy


@pytest.mark.parametrize("missing", ("main.py", "meow", "sudoku", "puzzle_common"))
def test_invalid_runtime_preserves_previous_site(monkeypatch, tmp_path, missing):
    project = _configure_fake_project(monkeypatch, tmp_path)
    target = project / missing
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    web = project / "build/web"
    web.mkdir(parents=True)
    (web / "keep.txt").write_text("keep")

    with pytest.raises(FileNotFoundError):
        build_web.build_web()

    assert (web / "keep.txt").is_file()


@pytest.mark.parametrize(
    "relative_path", (".", "build", "build/..", "build/unknown", "../outside")
)
def test_cleanup_rejects_unrecognized_paths(monkeypatch, tmp_path, relative_path):
    project = _configure_fake_project(monkeypatch, tmp_path)
    build = project / "build"
    build.mkdir()
    (build / "keep.txt").write_text("keep")
    with pytest.raises(RuntimeError):
        build_web._clear_build_directory(project / relative_path)
    assert (build / "keep.txt").is_file()


def test_cleanup_rejects_symlink_to_external_files(monkeypatch, tmp_path):
    project = _configure_fake_project(monkeypatch, tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    stage = project / "build/puzzle-solvers"
    stage.parent.mkdir()
    try:
        stage.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this system")
    with pytest.raises(RuntimeError):
        build_web._clear_build_directory(stage)
    assert (outside / "keep.txt").is_file()
