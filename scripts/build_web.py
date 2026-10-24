"""Build one Pygbag application and redirects for previous puzzle URLs."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = PROJECT_ROOT / "build"
WEB_OUTPUT = BUILD_ROOT / "web"
APP_NAME = "puzzle-solvers"
RUNTIME_PACKAGES = ("puzzle_common", "meow", "sudoku")


def _stage_root() -> Path:
    return BUILD_ROOT / APP_NAME


def _clear_build_directory(path: Path) -> None:
    """Remove one known build subtree without allowing broader deletion."""
    resolved = path.resolve()
    build_root = BUILD_ROOT.resolve()
    if (
        build_root != PROJECT_ROOT.resolve() / "build"
        or path not in {_stage_root(), WEB_OUTPUT}
        or resolved != path.absolute()
        or resolved == build_root
        or not resolved.is_relative_to(build_root)
    ):
        raise RuntimeError(
            f"지정된 빌드 하위 디렉터리만 삭제할 수 있습니다: {resolved}"
        )
    if resolved.is_dir():
        shutil.rmtree(resolved)


def stage_runtime_files() -> Path:
    """Copy the shared entry point, both puzzle definitions, and runtime assets."""
    stage_root = _stage_root()
    entry_point = PROJECT_ROOT / "main.py"
    if not entry_point.is_file():
        raise FileNotFoundError(f"Pygbag 진입점을 찾을 수 없습니다: {entry_point}")
    for name in RUNTIME_PACKAGES:
        package = PROJECT_ROOT / name
        if not package.is_dir():
            raise FileNotFoundError(
                f"애플리케이션 패키지를 찾을 수 없습니다: {package}"
            )
    _clear_build_directory(stage_root)
    stage_root.mkdir(parents=True)
    shutil.copy2(entry_point, stage_root / "main.py")
    for name in RUNTIME_PACKAGES:
        shutil.copytree(
            PROJECT_ROOT / name,
            stage_root / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
    return stage_root


def pygbag_command() -> list[str]:
    """Return the pinned build command for the single application."""
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
        "1010",
        "--height",
        "700",
        "--app_name",
        APP_NAME,
        "--package",
        "io.github.june2358.puzzle_solvers",
        "--title",
        "Puzzle Solvers",
        "--build",
        str(_stage_root()),
    ]


def _validate_pygbag_output(output: Path) -> None:
    """Reject incomplete output before it can become a Pages artifact."""
    if not (output / "index.html").is_file():
        raise RuntimeError("Pygbag Web 산출물에 index.html이 없습니다.")
    if sum(path.is_file() for path in output.glob("*.apk")) != 1:
        raise RuntimeError(
            "Pygbag Web 산출물에는 애플리케이션 APK가 하나 있어야 합니다."
        )


def build_web() -> None:
    """Validate the complete single bundle before replacing the deployable site."""
    environment = os.environ.copy()
    environment.setdefault("PYTHONUTF8", "1")
    stage_root = stage_runtime_files()
    subprocess.run(pygbag_command(), cwd=PROJECT_ROOT, env=environment, check=True)
    output = stage_root / "build/web"
    _validate_pygbag_output(output)
    _clear_build_directory(WEB_OUTPUT)
    shutil.copytree(output, WEB_OUTPUT)
    for key in ("meow", "sudoku"):
        redirect = WEB_OUTPUT / key
        redirect.mkdir()
        target = f"../?puzzle={key}"
        (redirect / "index.html").write_text(
            '<!doctype html>\n<html lang="ko">\n<meta charset="utf-8">\n'
            f'<meta http-equiv="refresh" content="0;url={target}">\n'
            f'<title>퍼즐 솔버</title>\n<a href="{target}">퍼즐 열기</a>\n</html>\n',
            encoding="utf-8",
        )
    print(f"Web build ready: {WEB_OUTPUT}")


if __name__ == "__main__":
    build_web()
