# Puzzle Solvers

MEOW Queens와 Sudoku를 함께 관리하는 pygame-ce 프로젝트입니다.
입력 화면, 풀이 재생 화면, 앱 실행 흐름과 웹 빌드를 공유합니다.
각 퍼즐의 규칙·솔버·입력 계약과 보드 표현은 작은 어댑터로 연결합니다.

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

- `meow/`, `sudoku/`: 퍼즐 모델·솔버·검증과 공통 화면에 연결하는 보드/단계 어댑터
- `puzzle_common/input_dialog.py`: 입력 레이아웃·버튼·프리셋·메시지·JSON/클립보드·이벤트 루프
- `puzzle_common/playback.py`: 풀이 패널·단계 이동·길게 누르기·자동 재생·이벤트 루프
- `puzzle_common/app.py`: 시작·편집·풀이·재생·편집 복귀·종료 흐름
- `puzzle_common/presentation.py`, 각 앱의 `presentation.py`: 공통 해 분류·단계 목록과 기존 솔버 결과의 연결
- `puzzle_common/layout.py`: 양쪽 입력/재생의 같은 창·보드·패널 배치
- `puzzle_common/`: 그 외 공통 폰트·그리기·좌표·클립보드·브라우저 입력·프리셋 파일 읽기
- `main_meow.py`, `main_sudoku.py`: 웹 빌드용 진입점
- `scripts/build_web.py`: 두 앱을 별도 번들로 빌드하고 선택 페이지 생성
- `tests/meow/`, `tests/sudoku/`: 기존 앱별 회귀 검사
- `docs/meow.md`, `docs/sudoku.md`: 퍼즐별 사용법과 풀이 정책

공통 코드를 수정한 뒤에는 전체 검사와 두 앱의 웹 빌드를 함께 실행합니다.
통합 전 두 프로젝트의 Git 이력은 이 저장소에 보존되어 있습니다.

공통 구현과 퍼즐 어댑터의 책임은 [구조 안내](docs/architecture.md)를 참고하세요.

양쪽 앱은 방향키·Tab 이동, 결과 배지와 해 없음의 편집 복귀 방식을 공유합니다.
알고리즘·퍼즐별 입력 규칙·숫자/후보 또는 고양이/색상 표현은 유지합니다.
