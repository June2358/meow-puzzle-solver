"""Build the production PyScript site with one shared application bundle."""

import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

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
        raise FileNotFoundError(
            f"애플리케이션 진입점을 찾을 수 없습니다: {entry_point}"
        )
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


def build_web() -> None:
    """Package the validated runtime once for the root PyScript site."""
    stage_root = stage_runtime_files()
    _clear_build_directory(WEB_OUTPUT)
    WEB_OUTPUT.mkdir(parents=True)
    with ZipFile(WEB_OUTPUT / "runtime.zip", "w", ZIP_DEFLATED) as archive:
        for path in sorted(stage_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(stage_root).as_posix())
    (WEB_OUTPUT / "pyscript.toml").write_text(
        '[files]\n"./runtime.zip" = "./*"\n', encoding="utf-8"
    )
    (WEB_OUTPUT / "index.html").write_text(
        """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Puzzle Solvers · PyScript</title>
  <link rel="stylesheet" href="https://pyscript.net/releases/2026.7.3/core.css">
  <script type="module" src="https://pyscript.net/releases/2026.7.3/core.js"></script>
  <style>
    body { margin: 0; min-height: 100dvh; background: #14161c;
           display: grid; place-items: center; }
    canvas { display: block; max-width: 100%; height: auto; }
  </style>
</head>
<body>
  <canvas id="canvas" aria-label="퍼즐 솔버"></canvas>
  <script type="py-game" config="pyscript.toml">
from puzzle_common.app import run_app

await run_app()
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )
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
    legacy = WEB_OUTPUT / "pyscript"
    legacy.mkdir()
    (legacy / "index.html").write_text(
        '<!doctype html>\n<html lang="ko">\n<meta charset="utf-8">\n'
        "<title>퍼즐 솔버</title>\n"
        '<script>location.replace("../" + location.search)</script>\n'
        '<a href="../">퍼즐 열기</a>\n</html>\n',
        encoding="utf-8",
    )
    print(f"PyScript site ready: {WEB_OUTPUT}")


if __name__ == "__main__":
    build_web()
