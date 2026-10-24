import shutil
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import build_web


def _configure_fake_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    project_root = tmp_path / "project"
    project_root.mkdir()
    for app in ("meow", "sudoku"):
        (project_root / f"main_{app}.py").write_text(
            f"from {app}.app import PLUGIN\nfrom puzzle_common.app import run_app\n",
            encoding="utf-8",
        )
        package = project_root / app
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "puzzles.json").write_text("{}", encoding="utf-8")

    common = project_root / "puzzle_common"
    fonts = common / "assets" / "fonts"
    fonts.mkdir(parents=True)
    (common / "__init__.py").write_text("", encoding="utf-8")
    (common / "runtime.py").write_text("FRAME_RATE = 60\n", encoding="utf-8")
    for filename in (
        "Pretendard-Regular.otf",
        "Pretendard-SemiBold.otf",
        "OFL-Pretendard.txt",
    ):
        (fonts / filename).write_bytes(filename.encode())

    monkeypatch.setattr(build_web, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(build_web, "BUILD_ROOT", project_root / "build")
    monkeypatch.setattr(build_web, "WEB_OUTPUT", project_root / "build" / "web")
    return project_root


@pytest.mark.parametrize(
    ("app", "stage_name"),
    [("meow", "meow-puzzle-solver"), ("sudoku", "simple-sudoku-solver")],
)
def test_stage_runtime_files_bundles_only_selected_app_and_shared_assets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    app: str,
    stage_name: str,
) -> None:
    project = _configure_fake_project(monkeypatch, tmp_path)
    for package in (project / app, project / "puzzle_common"):
        cache = package / "__pycache__"
        cache.mkdir()
        (cache / "module.pyc").write_bytes(b"bytecode")
        (package / "module.pyo").write_bytes(b"bytecode")
    (project / "README.md").write_text("docs", encoding="utf-8")
    (project / "tests").mkdir()
    (project / "tests" / "test_app.py").write_text("", encoding="utf-8")
    sibling = project / "build" / "unrelated-build"
    sibling.mkdir(parents=True)
    (sibling / "keep.txt").write_text("keep", encoding="utf-8")
    stage = project / "build" / stage_name
    stage.mkdir()
    (stage / "stale.py").write_text("old", encoding="utf-8")

    assert build_web.stage_runtime_files(app) == stage

    files = {
        path.relative_to(stage).as_posix()
        for path in stage.rglob("*")
        if path.is_file()
    }
    assert files == {
        "main.py",
        f"{app}/__init__.py",
        f"{app}/puzzles.json",
        "puzzle_common/__init__.py",
        "puzzle_common/runtime.py",
        "puzzle_common/assets/fonts/Pretendard-Regular.otf",
        "puzzle_common/assets/fonts/Pretendard-SemiBold.otf",
        "puzzle_common/assets/fonts/OFL-Pretendard.txt",
    }
    assert (stage / "main.py").read_bytes() == (project / f"main_{app}.py").read_bytes()
    assert (
        stage / "puzzle_common/assets/fonts/Pretendard-Regular.otf"
    ).read_bytes() == (
        project / "puzzle_common/assets/fonts/Pretendard-Regular.otf"
    ).read_bytes()
    assert (sibling / "keep.txt").read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("missing", ["main_meow.py", "meow", "puzzle_common"])
def test_staging_validates_runtime_before_removing_previous_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    missing: str,
) -> None:
    project = _configure_fake_project(monkeypatch, tmp_path)
    path = project / missing
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    stage = project / "build" / "meow-puzzle-solver"
    stage.mkdir(parents=True)
    (stage / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        build_web.stage_runtime_files("meow")

    assert (stage / "keep.txt").is_file()


@pytest.mark.parametrize("app", ["", "../outside", "meow/../../outside", "unknown"])
@pytest.mark.parametrize("operation", ["stage_runtime_files", "pygbag_command"])
def test_build_operations_reject_apps_outside_the_whitelist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    app: str,
    operation: str,
) -> None:
    _configure_fake_project(monkeypatch, tmp_path)

    with pytest.raises(ValueError):
        getattr(build_web, operation)(app)


@pytest.mark.parametrize(
    ("app", "stage_name", "width", "package", "title"),
    [
        (
            "meow",
            "meow-puzzle-solver",
            "980",
            "io.github.june2358.meow_puzzle_solver",
            "MEOW — Queens Puzzle Solver",
        ),
        (
            "sudoku",
            "simple-sudoku-solver",
            "960",
            "io.github.june2358.simple_sudoku_solver",
            "Sudoku Solver",
        ),
    ],
)
def test_pygbag_command_preserves_each_apps_identity_and_web_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    app: str,
    stage_name: str,
    width: str,
    package: str,
    title: str,
) -> None:
    project = _configure_fake_project(monkeypatch, tmp_path)

    command = build_web.pygbag_command(app)

    assert command[-1] == str(project / "build" / stage_name)
    assert command[1:3] == ["-m", "pygbag"]
    assert "--build" in command
    assert "--no_opt" in command
    for option, value in (
        ("--PYBUILD", "3.12"),
        ("--ume_block", "0"),
        ("--can_close", "1"),
        ("--width", width),
        ("--height", "680"),
        ("--app_name", stage_name),
        ("--package", package),
        ("--title", title),
    ):
        assert command[command.index(option) + 1] == value


def test_build_web_publishes_both_generated_apps_and_a_korean_selection_page(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = _configure_fake_project(monkeypatch, tmp_path)
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    web = project / "build" / "web"
    for folder in (web, web / "meow", web / "sudoku"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "stale.txt").write_text("old", encoding="utf-8")
    calls: list[SimpleNamespace] = []

    def fake_run(command, *, cwd, env, check):  # noqa: ANN001, ANN202
        calls.append(SimpleNamespace(command=command, cwd=cwd, env=env, check=check))
        stage = Path(command[-1])
        output = stage / "build" / "web"
        output.mkdir(parents=True)
        (output / "index.html").write_text("<html></html>", encoding="utf-8")
        (output / f"{stage.name}.apk").write_bytes(b"apk")
        (output / "runtime.js").write_text("// runtime", encoding="utf-8")

    monkeypatch.setattr(build_web.subprocess, "run", fake_run)

    build_web.build_web()

    assert [Path(call.command[-1]).name for call in calls] == [
        "meow-puzzle-solver",
        "simple-sudoku-solver",
    ]
    assert all(call.cwd == project and call.check is True for call in calls)
    assert all(call.env["PYTHONUTF8"] == "1" for call in calls)
    assert {
        path.relative_to(web).as_posix() for path in web.rglob("*") if path.is_file()
    } == {
        "index.html",
        "meow/index.html",
        "meow/meow-puzzle-solver.apk",
        "meow/runtime.js",
        "sudoku/index.html",
        "sudoku/simple-sudoku-solver.apk",
        "sudoku/runtime.js",
    }
    index = (web / "index.html").read_text(encoding="utf-8")
    assert 'lang="ko"' in index
    assert 'href="meow/"' in index
    assert 'href="sudoku/"' in index
    assert "퍼즐" in index
    assert (project / "build/meow-puzzle-solver/main.py").is_file()
    assert (project / "build/simple-sudoku-solver/main.py").is_file()


@pytest.mark.parametrize(
    "incomplete_app", ["meow-puzzle-solver", "simple-sudoku-solver"]
)
@pytest.mark.parametrize("missing", ["index.html", "APK"])
def test_build_web_rejects_incomplete_output_without_removing_the_previous_site(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    incomplete_app: str,
    missing: str,
) -> None:
    project = _configure_fake_project(monkeypatch, tmp_path)
    web = project / "build" / "web"
    web.mkdir(parents=True)
    (web / "keep.txt").write_text("keep", encoding="utf-8")

    def fake_run(command, **kwargs):  # noqa: ANN001, ANN202
        stage = Path(command[-1])
        output = stage / "build" / "web"
        output.mkdir(parents=True)
        if stage.name != incomplete_app or missing != "index.html":
            (output / "index.html").write_text("<html></html>", encoding="utf-8")
        if stage.name != incomplete_app or missing != "APK":
            (output / f"{stage.name}.apk").write_bytes(b"apk")

    monkeypatch.setattr(build_web.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match=missing):
        build_web.build_web()

    assert (web / "keep.txt").read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize(
    "relative_path", [".", "build", "build/..", "build/unknown", "../outside"]
)
def test_cleanup_rejects_project_build_and_unrecognized_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    relative_path: str,
) -> None:
    project = _configure_fake_project(monkeypatch, tmp_path)
    build = project / "build"
    build.mkdir()
    (project / "keep.txt").write_text("keep", encoding="utf-8")
    (build / "keep.txt").write_text("keep", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(RuntimeError):
        build_web._clear_build_directory(project / relative_path)

    assert (project / "keep.txt").is_file()
    assert (build / "keep.txt").is_file()
    assert (outside / "keep.txt").is_file()


def test_cleanup_rejects_a_build_symlink_to_external_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = _configure_fake_project(monkeypatch, tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep", encoding="utf-8")
    stage = project / "build" / "meow-puzzle-solver"
    stage.parent.mkdir()
    try:
        stage.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this system")

    with pytest.raises(RuntimeError):
        build_web._clear_build_directory(stage)

    assert (outside / "keep.txt").is_file()


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

    assert project["dependency-groups"]["web"] == ["pygbag==0.9.3"]
