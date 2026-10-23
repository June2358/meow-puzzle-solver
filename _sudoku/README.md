# Sudoku Solver & Visualizer

9×9 스도쿠를 쉬운 논리 기법과 깊이 1의 가정으로 먼저 풀고, 사람이 설명하기 어려운 지점부터는 MRV 백트래킹으로 완성하는 pygame 애플리케이션입니다. Windows에서 pygame으로 실행하거나 웹페이지에서 바로 사용할 수 있습니다.

## 주요 기능

- GUI에서 직접 숫자를 입력하거나 내장 예제 문제를 불러올 수 있습니다.
- 외부 OCR/비전 AI가 만든 **JSON 9×9 행렬**을 그대로 붙여넣을 수 있습니다.
- 기본 논리가 멈추면 모든 2후보 셀의 후보를 직접 전파력(H1) 순서로 하나씩 가정합니다.
- 모순이면 그 후보만 제거하고, 가정에서 해가 완성되면 대표 해로 보관합니다.
- 모든 2후보 가정이 정체되면 설명을 종료하고 MRV 백트래킹으로 해 하나를 찾습니다.
- 각 풀이 단계를 불변 스냅샷으로 기록하고 GUI에서 앞뒤로 확인할 수 있습니다.
- 결과를 `유일해`, `복수해`, `해 없음`의 세 상태로 구분합니다.

애플리케이션 안에는 OCR 엔진이나 외부 AI API가 들어 있지 않습니다. 이미지 인식은 사용자가 선택한 외부 도구에서 수행하고, 이 프로젝트는 그 결과 형식만 엄격하게 검증합니다.

## 실행

### 홈페이지

설치 없이 [웹페이지](https://june2358.github.io/simple-sudoku-solver/)에서 바로 실행할 수 있습니다.

### pygame

- Windows 10/11 (`win-64`)
- Python 3.12.2
- pygame-ce 2.5.8
- [uv](https://docs.astral.sh/uv/)

pygame 화면은 [Pretendard v1.3.9](https://github.com/orioncactus/pretendard/releases/tag/v1.3.9)의 Regular와 SemiBold를 번들하며 [SIL Open Font License 1.1](sudoku/assets/fonts/OFL-Pretendard.txt)을 따릅니다. Desktop과 Web 모두 같은 실제 weight 파일을 사용합니다.

최초 환경 준비:

```powershell
uv sync
```

실행:

```powershell
uv run python -m sudoku
```

### 개발 검사

전체 테스트와 정적 검사는 다음 명령으로 실행합니다.

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest -q -W error
```

## 문제 입력

### 직접 입력

- 마우스 클릭 또는 화살표 키: 칸 선택
- 숫자 키 `1`~`9`: 숫자 입력
- `0`, `Delete`, `Backspace`: 숫자 삭제
- 난이도 버튼: 내장 문제 불러오기
- `Enter` 또는 `S`: 풀이 시작

행·열·3×3 박스에 같은 숫자가 중복되면 충돌 칸을 표시하고 풀이를 시작하지 않습니다.

### 내장 프리셋

화면에는 `쉬움`부터 `극한`까지의 이름만 표시합니다. 각 문제는 아래 풀이 경로를 대표하는 예제로 선정했습니다.

| 프리셋 | 실제 풀이 경로 |
|---|---|
| 쉬움 | Full House와 Naked / Hidden Single만 사용 |
| 보통 | Locked Pair까지 사용 |
| 어려움 | Hidden Triple까지 사용하되 가정 없이 완성 |
| 전문가 | 한 번의 2후보 가정에서 모순을 증명한 뒤 완성 |
| 마스터 | 서로 다른 정체점에서 두 번 이상 모순을 증명한 뒤 완성 |
| 극한 | 허용된 모든 2후보 가정이 정체되어 MRV 탐색으로 전환 |

`극한` 프리셋은 사람식 가정과 백트래킹의 경계를 보여 주는 예제입니다. 제품은 사람식 가정 범위를 더 늘리지 않고, 이 지점에서 명시적으로 백트래킹으로 전환합니다.

### 외부 AI OCR 결과 붙여넣기

Desktop에서는 `프롬프트 복사`와 `JSON 붙여넣기`가 운영체제 클립보드를
사용하며 `Ctrl+V`도 지원합니다. Web에서는 `프롬프트 보기`가 선택 가능한
read-only textarea를 열고, `JSON 입력`이 실제 HTML textarea를 엽니다.
모바일에서는 이 입력칸을 길게 눌러 브라우저의 기본 붙여넣기를 사용합니다.
Web 앱은 클립보드 읽기 권한을 요청하지 않습니다.

프롬프트와 스도쿠 이미지를 외부 비전 AI에 함께 전달한 뒤, AI가 반환한
JSON만 불러옵니다. 결과는 반드시 화면에서 원본 이미지와 대조해야 합니다.

허용하는 형식은 다음과 같습니다.

- 최상위 값은 배열 하나여야 합니다.
- 행 9개, 각 행의 값 9개가 정확히 있어야 합니다.
- 값은 JSON 정수 `0`~`9`만 허용합니다. 빈칸은 `0`입니다.
- 문자열, `true`/`false`, `null`, 객체 래퍼, Markdown 코드 펜스, 설명 문장은 허용하지 않습니다.

프롬프트의 단일 원본은 애플리케이션의
[`sudoku/matrix_input.py`](sudoku/matrix_input.py)에 있습니다. 화면의 복사
버튼을 사용하면 항상 현재 버전을 가져옵니다.

형식이 잘못된 붙여넣기는 기존 입력을 바꾸지 않습니다. 형식은 맞지만 스도쿠 규칙과 충돌하는 값은 편집 화면에서 표시하며, 수정하기 전까지 풀이를 시작할 수 없습니다.

## 웹페이지 범위와 제한

- 첫 접속에는 브라우저 실행에 필요한 파일을 받아야 하므로 네트워크가
  필요합니다. PWA/offline 설치는 현재 범위가 아닙니다.
- 모바일은 JSON 붙여넣기, 보드 확인, 풀이 시작, 결과 단계 이동을 우선
  지원합니다. 화면 숫자패드나 휴대폰 전용 앱 레이아웃은 제공하지 않습니다.
- 웹 화면은 viewport에 맞춰 같은 비율로 축소됩니다. 세로
  화면에서는 보드와 pygame 버튼이 작아질 수 있지만 JSON textarea는 실제
  브라우저 입력창과 48px 이상의 버튼을 사용합니다.

## 풀이 정책

솔버가 사용자에게 보여 주는 풀이 경로는 다음 순서를 따릅니다.

1. `Full House → Naked Single → Hidden Single → Locked Pair → Naked Pair → Locked Candidates — Pointing → Locked Candidates — Claiming → Locked Triple → Naked Triple → Hidden Pair → Hidden Triple` 순서로 기본 기법을 고정점까지 적용합니다. Full House와 Single 단계는 시작 시점의 후보 상태를 고정하고, 같은 기법으로 이미 확정 가능한 모든 칸을 한꺼번에 채웁니다. 그 배치로 새롭게 확정 가능해진 칸은 다음 단계에서 처리합니다. 전체 보드의 마지막 Full House는 `Last Digit`으로 표시합니다.
2. 정체되면 후보가 정확히 2개인 모든 셀의 후보를 가정 대상으로 모읍니다. 가정 자체는 제외하고, 각 가정을 바로 적용했을 때 새롭게 후보가 하나로 줄어드는 셀 제약과 하우스-숫자 제약의 수를 H1으로 계산해 높은 순서부터 시험합니다.
3. H1이 같으면 같은 점수에서 아직 시험하지 않은 가정을 먼저 선택합니다. 모두 정체 이력이 있다면 가장 오래전에 시험한 가정을 먼저 순환시키고, 마지막 동률만 행·열·후보 숫자 오름차순으로 정합니다.
4. 각 후보는 서로 독립적으로 한 번만 가정하고, 추가 가정 없이 기존 논리를 계속 적용합니다. 모순이 나온 후보만 원래 상태에서 제거한 뒤 1번부터 다시 시작하며, 바뀐 상태에서는 H1을 전부 다시 계산합니다.
5. 가정에서 해 하나가 완성되면 그 해를 즉시 유효한 대표 해로 보관합니다. 나머지 후보는 화면에서 더 시험하지 않으며, 별도의 조용한 완전 탐색이 다른 해의 존재를 확인합니다. 대표 해 발견 자체는 유일해라는 뜻이 아닙니다.
6. 모든 2후보 가정이 모순도 완성도 없이 정체되거나 2후보 셀이 없으면, 화면에 경계를 표시하고 재귀 MRV 백트래킹으로 전환합니다.

가정 안에서 다시 가정하는 중첩 추론은 풀이 단계에 포함하지 않습니다. 따라서 표시되는 모든 가정의 깊이는 항상 1 이하입니다. 백트래킹은 화면에 재귀 분기를 늘어놓지 않고 조용히 실행하며, 서로 다른 해를 최대 두 개까지만 찾아 결과를 판정합니다.

## 풀이 결과

| 상태 | 의미 | 동작 |
|---|---|---|
| 유일해 (`SOLVED_UNIQUE`) | 가능한 완성 보드가 정확히 하나 | 단계별 시각화 화면으로 이동 |
| 복수해 (`SOLVED_MULTIPLE`) | 서로 다른 완성 보드가 둘 이상 | 가능한 해 중 하나를 표시하고 화면에 복수해 경고를 계속 표시 |
| 해 없음 (`UNSOLVABLE`) | 조건을 만족하는 완성 보드가 없음 | 입력 화면에서 오류 안내 |

솔버는 첫 해를 찾은 뒤 두 번째 해의 존재 여부까지만 확인합니다. 복수해의 정확한 총개수는 계산하지 않으며, 표시된 보드는 여러 가능한 해 중 하나일 뿐입니다.

## 프로젝트 구조

```text
00_SUDOKU/
├── main.py                     # 공통 앱 진입점
├── .github/workflows/
│   ├── ci.yml                  # Windows 자동 검사
│   └── pages.yml               # 웹페이지 빌드·게시 자동화
├── scripts/
│   └── build_web.py            # Pygbag 웹 산출물 생성
├── sudoku/
│   ├── __main__.py             # python -m sudoku 진입점
│   ├── app.py                  # 입력/풀이/시각화 화면 흐름
│   ├── board.py                # 불변 Puzzle과 입력 검증
│   ├── topology.py             # 셀·유닛·피어 관계
│   ├── solver_state.py         # 풀이 중 사용하는 가변 값과 후보 상태
│   ├── solve_types.py          # 풀이 결과와 단계 자료형
│   ├── techniques.py           # 동일 스냅샷 기준 논리 배치 탐색
│   ├── solver.py               # 기본 논리, 2후보 H1 one-ply, 조용한 MRV 탐색
│   ├── input_dialog.py         # 직접 입력 및 JSON 붙여넣기
│   ├── matrix_input.py         # 외부 AI 프롬프트와 클립보드 처리
│   ├── matrix_parser.py        # OCR JSON 행렬 형식 검증
│   ├── web_text_dialog.py      # Web 전용 일회성 DOM textarea
│   ├── runtime.py              # 공통 frame pacing과 browser yield
│   ├── puzzle_catalog.py       # 내장 프리셋 로딩과 검증
│   ├── visualizer.py           # 기록된 단계 시각화
│   ├── ui_style.py             # 공용 색상·폰트·그리기
│   ├── ui_components.py        # 공용 UI 컴포넌트
│   ├── assets/fonts/           # 번들 한글 폰트와 OFL
│   └── puzzles.json            # 검증된 내장 문제
├── tests/
├── .python-version             # Python 3.12.2
├── pyproject.toml              # 의존성 및 Ruff 설정
├── uv.lock                     # 재현 가능한 전체 의존성 잠금
└── README.md
```

## 시각화 화면

- `←`, `→`: 이전/다음 단계
- `Space`: 자동 재생 또는 일시정지
- `Home`, `End`: 첫 단계/마지막 단계
- `Esc`: 현재 문제를 유지한 채 입력 화면으로 돌아가기
