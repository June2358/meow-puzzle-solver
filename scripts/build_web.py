"""Build isolated Pygbag applications and a shared puzzle selection page."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = PROJECT_ROOT / "build"
WEB_OUTPUT = BUILD_ROOT / "web"
APPLICATIONS = {
    "meow": (
        "meow-puzzle-solver",
        "980",
        "io.github.june2358.meow_puzzle_solver",
        "MEOW — Queens Puzzle Solver",
    ),
    "sudoku": (
        "simple-sudoku-solver",
        "960",
        "io.github.june2358.simple_sudoku_solver",
        "Sudoku Solver",
    ),
}


def _stage_root(app: str) -> Path:
    if app not in APPLICATIONS:
        raise ValueError(f"지원하지 않는 애플리케이션입니다: {app}")
    return BUILD_ROOT / APPLICATIONS[app][0]


def _clear_build_directory(path: Path) -> None:
    """Remove one known build subtree without allowing broader deletion."""

    resolved = path.resolve()
    build_root = BUILD_ROOT.resolve()
    allowed = {BUILD_ROOT / settings[0] for settings in APPLICATIONS.values()}
    allowed.add(WEB_OUTPUT)
    if (
        build_root != PROJECT_ROOT.resolve() / "build"
        or path not in allowed
        or resolved != path.absolute()
        or resolved == build_root
        or not resolved.is_relative_to(build_root)
    ):
        raise RuntimeError(
            f"지정된 빌드 하위 디렉터리만 삭제할 수 있습니다: {resolved}"
        )
    if resolved.is_dir():
        shutil.rmtree(resolved)


def stage_runtime_files(app: str) -> Path:
    """Copy only files required by the browser runtime into the Pygbag app."""

    stage_root = _stage_root(app)
    entry_point = PROJECT_ROOT / f"main_{app}.py"
    if not entry_point.is_file():
        raise FileNotFoundError(f"Pygbag 진입점을 찾을 수 없습니다: {entry_point}")
    for name in (app, "puzzle_common"):
        package = PROJECT_ROOT / name
        if not package.is_dir():
            raise FileNotFoundError(
                f"애플리케이션 패키지를 찾을 수 없습니다: {package}"
            )

    _clear_build_directory(stage_root)
    stage_root.mkdir(parents=True)
    shutil.copy2(entry_point, stage_root / "main.py")
    for name in (app, "puzzle_common"):
        shutil.copytree(
            PROJECT_ROOT / name,
            stage_root / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
    return stage_root


def pygbag_command(app: str) -> list[str]:
    """Return the pinned Pygbag build command for this application."""

    stage_root = _stage_root(app)
    app_name, width, package, title = APPLICATIONS[app]
    return [
        sys.executable,
        "-m",
        "pygbag",
        "--no_opt",
        "--ume_block",
        "0",
        "--can_close",
        "1",
        "--PYBUILD",
        "3.12",
        "--width",
        width,
        "--height",
        "680",
        "--app_name",
        app_name,
        "--package",
        package,
        "--title",
        title,
        "--build",
        str(stage_root),
    ]


def _validate_pygbag_output(output: Path) -> None:
    """Reject incomplete output before it can become a Pages artifact."""

    if not (output / "index.html").is_file():
        raise RuntimeError("Pygbag Web 산출물에 index.html이 없습니다.")
    if not any(path.is_file() for path in output.glob("*.apk")):
        raise RuntimeError("Pygbag Web 산출물에 애플리케이션 APK가 없습니다.")


def build_web() -> None:
    """Build both applications before replacing the deployable site."""

    environment = os.environ.copy()
    environment.setdefault("PYTHONUTF8", "1")
    for app in APPLICATIONS:
        stage_root = stage_runtime_files(app)
        subprocess.run(
            pygbag_command(app),
            cwd=PROJECT_ROOT,
            env=environment,
            check=True,
        )
        _validate_pygbag_output(stage_root / "build" / "web")

    _clear_build_directory(WEB_OUTPUT)
    for app in APPLICATIONS:
        shutil.copytree(_stage_root(app) / "build" / "web", WEB_OUTPUT / app)
    (WEB_OUTPUT / "index.html").write_text(
        '<!doctype html>\n<html lang="ko">\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>퍼즐 솔버</title>\n<h1>퍼즐을 선택하세요</h1>\n"
        '<ul><li><a href="meow/">MEOW 퀸즈 퍼즐</a></li>\n'
        '<li><a href="sudoku/">스도쿠</a></li></ul>\n</html>\n',
        encoding="utf-8",
    )
    print(f"Web build ready: {WEB_OUTPUT}")


if __name__ == "__main__":
    build_web()
