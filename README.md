# Puzzle Solvers

MEOW Queens와 Sudoku를 하나의 pygame-ce 앱에서 입력하고 풀고 재생합니다.
앱 안에서 퍼즐을 선택하며 두 모드가 같은 편집기·보드 렌더러·재생기와 조작을 사용합니다.
각 퍼즐의 규칙, 풀이 순서와 해 판정은 그대로 유지합니다.

공식 통합 저장소: <https://github.com/June2358/puzzle-solvers>

- [웹에서 퍼즐 선택](https://june2358.github.io/puzzle-solvers/)
- [MEOW Queens로 시작](https://june2358.github.io/puzzle-solvers/meow/)
- [Sudoku로 시작](https://june2358.github.io/puzzle-solvers/sudoku/)

## 실행

Python 3.12.15와 uv를 사용합니다.

```powershell
uv sync --locked
uv run python main.py
```

`uv run python -m puzzle_common`도 같은 선택 화면을 엽니다.
Windows에서는 `run.cmd`를 실행하세요. `run.cmd meow`, `run.cmd sudoku` 또는
`uv run python -m meow`, `uv run python -m sudoku`는 해당 모드의 편집기로 시작합니다.

선택 화면에서는 마우스나 방향키·Tab·Enter를 사용합니다.
편집기의 Esc는 퍼즐 선택으로, 재생기의 Esc 또는 편집 버튼은 원본 문제 편집으로 돌아갑니다.
앱을 실행하는 동안 각 모드의 초안이 따로 유지됩니다. 창을 닫으면 앱이 종료됩니다.

## 검사

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

`http://localhost:8765/`에서 앱 안의 선택 화면을 엽니다.
두 퍼즐과 공통 자산을 포함한 Pygbag 번들을 한 번 빌드하고 `build/web`에 배치합니다.
기존 `/meow/`, `/sudoku/` 주소는 각각 `/?puzzle=meow`, `/?puzzle=sudoku`로 이동하며
같은 앱에서 해당 모드로 시작합니다. 모드를 바꿀 때 페이지를 다시 불러오지 않습니다.

GitHub Actions는 pull request에서 웹 빌드를 검사하고 `main` 갱신 시 같은 산출물을 Pages에 배포합니다.
새 GitHub 저장소에서는 Settings → Pages → Source를 GitHub Actions로 선택합니다.

## 구조

- `main.py`, `puzzle_common/__main__.py`: 하나의 앱 진입점
- `puzzle_common/app.py`: 명시적 퍼즐 등록, 선택 → 편집 → 풀이 → 재생과 초안 보존
- `puzzle_common/puzzle.py`, `view.py`: 퍼즐 정의와 불변 표시 데이터 계약
- `puzzle_common/input_dialog.py`, `board.py`, `playback.py`: 공통 편집기·렌더러·재생기
- `puzzle_common/engine.py`: 논리 고정점·가정·반증·탐색과 불변 실행 기록, 공통 SolveResult
- `puzzle_common/presentation.py`: 원본 실행 기록의 단계 변환과 공통 풀이 설명
- `meow/definition.py`, `sudoku/definition.py`: 규칙·파서·프롬프트·예제와 상태·추론 데이터 제공
- `meow/`, `sudoku/`: 퍼즐 모델·고유 검증·기법·알고리즘과 예제
- `scripts/build_web.py`: 단일 웹 번들과 기존 주소의 연결 페이지 생성
- `tests/common/`, `tests/meow/`, `tests/sudoku/`: 공통 계약과 퍼즐별 회귀 검사

두 프로젝트의 통합 전 Git 이력도 이 저장소에 보존되어 있습니다.
