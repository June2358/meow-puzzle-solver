"""Stage the runtime-only app and produce a deployable Pygbag site."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = PROJECT_ROOT / "build"
STAGE_ROOT = BUILD_ROOT / "simple-sudoku-solver"
PYGBAG_OUTPUT = STAGE_ROOT / "build" / "web"
WEB_OUTPUT = BUILD_ROOT / "web"


def _clear_build_directory(path: Path) -> None:
    """Remove one known build subtree without allowing broader deletion."""

    resolved = path.resolve()
    if not resolved.is_relative_to(BUILD_ROOT.resolve()):
        raise RuntimeError(f"빌드 디렉터리 밖은 삭제할 수 없습니다: {resolved}")
    if resolved.is_dir():
        shutil.rmtree(resolved)


def stage_runtime_files() -> None:
    """Copy only files required by the browser runtime into the Pygbag app."""

    entry_point = PROJECT_ROOT / "main.py"
    package = PROJECT_ROOT / "sudoku"
    if not entry_point.is_file():
        raise FileNotFoundError(f"Pygbag 진입점을 찾을 수 없습니다: {entry_point}")
    if not package.is_dir():
        raise FileNotFoundError(f"애플리케이션 패키지를 찾을 수 없습니다: {package}")

    _clear_build_directory(STAGE_ROOT)
    STAGE_ROOT.mkdir(parents=True)
    shutil.copy2(entry_point, STAGE_ROOT / "main.py")
    shutil.copytree(
        package,
        STAGE_ROOT / "sudoku",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )


def pygbag_command() -> list[str]:
    """Return the pinned Pygbag build command for this application."""

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
        "960",
        "--height",
        "680",
        "--app_name",
        "simple-sudoku-solver",
        "--package",
        "io.github.june2358.simple_sudoku_solver",
        "--title",
        "Sudoku Solver",
        "--build",
        str(STAGE_ROOT),
    ]


def _validate_pygbag_output() -> None:
    """Reject incomplete output before it can become a Pages artifact."""

    if not (PYGBAG_OUTPUT / "index.html").is_file():
        raise RuntimeError("Pygbag Web 산출물에 index.html이 없습니다.")
    if not tuple(PYGBAG_OUTPUT.glob("*.apk")):
        raise RuntimeError("Pygbag Web 산출물에 애플리케이션 APK가 없습니다.")


def build_web() -> None:
    """Build the Pygbag application and copy only its deployable output."""

    stage_runtime_files()
    _clear_build_directory(WEB_OUTPUT)

    environment = os.environ.copy()
    environment.setdefault("PYTHONUTF8", "1")
    subprocess.run(
        pygbag_command(),
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
    )

    _validate_pygbag_output()
    shutil.copytree(PYGBAG_OUTPUT, WEB_OUTPUT)
    print(f"Web build ready: {WEB_OUTPUT}")


if __name__ == "__main__":
    build_web()
