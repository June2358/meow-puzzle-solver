import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import build_web


def _configure_fake_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    project_root = tmp_path / "project"
    build_root = project_root / "build"
    stage_root = build_root / "simple-sudoku-solver"
    pygbag_output = stage_root / "build" / "web"
    web_output = build_root / "web"

    project_root.mkdir()
    (project_root / "main.py").write_text("print('web')\n", encoding="utf-8")
    package = project_root / "sudoku"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(build_web, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(build_web, "BUILD_ROOT", build_root)
    monkeypatch.setattr(build_web, "STAGE_ROOT", stage_root)
    monkeypatch.setattr(build_web, "PYGBAG_OUTPUT", pygbag_output)
    monkeypatch.setattr(build_web, "WEB_OUTPUT", web_output)
    return stage_root, pygbag_output, web_output


def test_stage_runtime_files_excludes_repository_and_bytecode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stage_root, _, _ = _configure_fake_project(monkeypatch, tmp_path)
    package = build_web.PROJECT_ROOT / "sudoku"
    (package / "puzzles.json").write_text("{}", encoding="utf-8")
    cache = package / "__pycache__"
    cache.mkdir()
    (cache / "module.pyc").write_bytes(b"bytecode")
    (build_web.PROJECT_ROOT / "README.md").write_text("docs", encoding="utf-8")

    build_web.stage_runtime_files()

    assert (stage_root / "main.py").is_file()
    assert (stage_root / "sudoku" / "puzzles.json").is_file()
    assert not (stage_root / "sudoku" / "__pycache__").exists()
    assert not (stage_root / "README.md").exists()


def test_pygbag_command_uses_pinned_web_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stage_root, _, _ = _configure_fake_project(monkeypatch, tmp_path)

    command = build_web.pygbag_command()

    assert command[-1] == str(stage_root)
    assert command[1:3] == ["-m", "pygbag"]
    assert "--build" in command
    assert command[command.index("--PYBUILD") + 1] == "3.12"
    assert command[command.index("--ume_block") + 1] == "0"
    assert command[command.index("--can_close") + 1] == "1"


def test_build_web_publishes_only_generated_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, pygbag_output, web_output = _configure_fake_project(monkeypatch, tmp_path)
    web_output.mkdir(parents=True)
    (web_output / "stale.txt").write_text("old", encoding="utf-8")
    calls: list[SimpleNamespace] = []

    def fake_run(command, *, cwd, env, check):  # noqa: ANN001, ANN202
        calls.append(SimpleNamespace(command=command, cwd=cwd, env=env, check=check))
        pygbag_output.mkdir(parents=True)
        (pygbag_output / "index.html").write_text("<html></html>", encoding="utf-8")
        (pygbag_output / "simple-sudoku-solver.apk").write_bytes(b"apk")

    monkeypatch.setattr(build_web.subprocess, "run", fake_run)

    build_web.build_web()

    assert len(calls) == 1
    assert calls[0].cwd == build_web.PROJECT_ROOT
    assert calls[0].check is True
    assert (web_output / "index.html").is_file()
    assert (web_output / "simple-sudoku-solver.apk").is_file()
    assert not (web_output / "stale.txt").exists()
    assert not (web_output / "main.py").exists()


def test_build_web_rejects_incomplete_pygbag_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_fake_project(monkeypatch, tmp_path)
    monkeypatch.setattr(build_web.subprocess, "run", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="index.html"):
        build_web.build_web()


def test_pages_workflow_uploads_only_the_web_build() -> None:
    workflow = (
        build_web.PROJECT_ROOT / ".github" / "workflows" / "pages.yml"
    ).read_text(encoding="utf-8")

    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "name: github-pages" in workflow
    assert "uv sync --locked --no-dev --group web" in workflow
    assert "python scripts/build_web.py" in workflow
    assert "actions/configure-pages@" in workflow
    assert "actions/upload-pages-artifact@" in workflow
    assert "actions/deploy-pages@" in workflow
    assert "path: build/web" in workflow
    assert "path: .\n" not in workflow


def test_pygbag_is_pinned_in_the_non_default_web_group() -> None:
    project = tomllib.loads(
        (build_web.PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert project["dependency-groups"]["web"] == ["pygbag==0.9.2"]
