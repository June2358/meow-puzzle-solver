# Puzzle Solvers

MEOW Queens와 Sudoku를 함께 관리하는 pygame-ce 프로젝트입니다.
각 퍼즐의 규칙과 솔버는 독립적으로 유지하며, 화면·입력·웹 실행 기반은 공유합니다.

## 개발 환경

Python 3.12.2와 uv를 사용합니다.

```powershell
uv sync --locked
uv run python -m meow
uv run python -m sudoku
```

검사:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest -q -W error
```

## 웹 빌드

```powershell
uv sync --locked --group web
uv run python scripts/build_web.py
uv run python -m http.server 8765 --directory build/web
```

`http://localhost:8765/`에서 앱을 선택합니다. 각각 `/meow/`, `/sudoku/`에 있습니다.
GitHub Actions는 `main` 갱신 시 두 앱을 빌드하고 `build/web`을 하나의 Pages 사이트로 배포합니다.
Pull request에서도 두 앱의 웹 빌드를 검사하며, 배포는 `main`에서만 실행합니다.
새 GitHub 저장소에서는 Settings → Pages → Source를 GitHub Actions로 선택합니다.

## 구조

- `meow/`, `sudoku/`: 각 앱의 모델, 입력 검증, 솔버, 보드와 풀이 시각화
- `puzzle_common/`: 공통 UI, 폰트, 클립보드, 브라우저 입력창, 프레임 처리
- `main_meow.py`, `main_sudoku.py`: 웹 빌드용 진입점
- `scripts/build_web.py`: 두 앱을 별도 번들로 빌드하고 선택 페이지 생성
- `tests/meow/`, `tests/sudoku/`: 기존 앱별 회귀 검사
- `docs/meow.md`, `docs/sudoku.md`: 퍼즐별 사용법과 풀이 정책

공통 코드를 수정한 뒤에는 전체 검사와 두 앱의 웹 빌드를 함께 실행합니다.
통합 전 두 프로젝트의 Git 이력은 이 저장소에 보존되어 있습니다.
