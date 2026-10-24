import shutil
import tomllib
from pathlib import Path
from types import SimpleNamespace

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


def test_command_builds_one_shared_runtime(monkeypatch, tmp_path):
    project = _configure_fake_project(monkeypatch, tmp_path)
    command = build_web.pygbag_command()
    assert command[-1] == str(project / "build/puzzle-solvers")
    assert command[1:3] == ["-m", "pygbag"]
    assert "--build" in command
    assert "--no_opt" in command
    for option, value in (
        ("--PYBUILD", "3.12"),
        ("--ume_block", "0"),
        ("--can_close", "1"),
        ("--width", "1010"),
        ("--height", "700"),
        ("--app_name", "puzzle-solvers"),
        ("--package", "io.github.june2358.puzzle_solvers"),
        ("--title", "Puzzle Solvers"),
    ):
        assert command[command.index(option) + 1] == value


def test_build_publishes_one_apk_with_compatibility_redirects(monkeypatch, tmp_path):
    project = _configure_fake_project(monkeypatch, tmp_path)
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    web = project / "build/web"
    web.mkdir(parents=True)
    (web / "stale.txt").write_text("stale")
    calls = []

    def fake_run(command, *, cwd, env, check):
        calls.append(SimpleNamespace(command=command, cwd=cwd, env=env, check=check))
        output = Path(command[-1]) / "build/web"
        output.mkdir(parents=True)
        (output / "index.html").write_text("<html>shared app</html>", encoding="utf-8")
        (output / "puzzle-solvers.apk").write_bytes(b"apk")
        (output / "runtime.js").write_text("// runtime")

    monkeypatch.setattr(build_web.subprocess, "run", fake_run)
    build_web.build_web()
    assert len(calls) == 1
    assert calls[0].cwd == project and calls[0].check is True
    assert calls[0].env["PYTHONUTF8"] == "1"
    assert {
        path.relative_to(web).as_posix() for path in web.rglob("*") if path.is_file()
    } == {
        "index.html",
        "puzzle-solvers.apk",
        "runtime.js",
        "meow/index.html",
        "sudoku/index.html",
    }
    assert (web / "index.html").read_text() == "<html>shared app</html>"
    for key in ("meow", "sudoku"):
        redirect = (web / key / "index.html").read_text(encoding="utf-8")
        assert f"url=../?puzzle={key}" in redirect
        assert f'href="../?puzzle={key}"' in redirect


@pytest.mark.parametrize("missing", ("index.html", "APK"))
def test_incomplete_output_preserves_previous_site(monkeypatch, tmp_path, missing):
    project = _configure_fake_project(monkeypatch, tmp_path)
    web = project / "build/web"
    web.mkdir(parents=True)
    (web / "keep.txt").write_text("keep")

    def fake_run(command, **kwargs):
        output = Path(command[-1]) / "build/web"
        output.mkdir(parents=True)
        if missing != "index.html":
            (output / "index.html").write_text("<html></html>")
        if missing != "APK":
            (output / "puzzle-solvers.apk").write_bytes(b"apk")

    monkeypatch.setattr(build_web.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match=missing):
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


def test_pages_workflow_uploads_only_the_web_build():
    workflow = (build_web.PROJECT_ROOT / ".github/workflows/pages.yml").read_text(
        encoding="utf-8"
    )
    for instruction in (
        "pages: write",
        "id-token: write",
        "name: github-pages",
        "uv sync --locked --no-dev --group web",
        "python scripts/build_web.py",
        "actions/configure-pages@",
        "actions/upload-pages-artifact@",
        "actions/deploy-pages@",
        "path: build/web",
    ):
        assert instruction in workflow
    assert "path: .\n" not in workflow


def test_pygbag_is_pinned_in_non_default_web_group():
    project = tomllib.loads(
        (build_web.PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert project["dependency-groups"]["web"] == ["pygbag==0.9.3"]


@pytest.mark.parametrize("apk_names", (("first.apk", "second.apk"), ()))
def test_generated_bundle_requires_exactly_one_apk(tmp_path, apk_names):
    (tmp_path / "index.html").write_text("<html></html>")
    for name in apk_names:
        (tmp_path / name).write_bytes(b"apk")
    (tmp_path / "directory.apk").mkdir()
    with pytest.raises(RuntimeError, match="APK"):
        build_web._validate_pygbag_output(tmp_path)
