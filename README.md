# MEOW — Queens Puzzle Solver

MEOW는 1★ Star Battle 규칙을 고양이 테마로 표현한
Queens 스타일 논리 퍼즐 솔버입니다. Queens의 왕관 대신 고양이를 배치하지만
퍼즐 규칙은 동일합니다.

## 퍼즐 규칙

- 각 행에는 고양이가 정확히 한 마리 있어야 합니다.
- 각 열에는 고양이가 정확히 한 마리 있어야 합니다.
- 각 색상 영역에는 고양이가 정확히 한 마리 있어야 합니다.
- 고양이끼리는 대각선을 포함하여 서로 인접할 수 없습니다.

전통적인 N-Queens와 달리 같은 대각선 전체를 금지하지는 않으며, 바로
인접한 대각선 칸에만 고양이를 함께 배치할 수 없습니다.

이 규칙은 퍼즐 장르상
[1★ Star Battle](https://www.gmpuzzles.com/blog/2024/10/bonus-star-battle-aka-queens-by-thomas-snyder-5/)에 해당하며,
[LinkedIn에서는 Queens](https://www.linkedin.com/help/linkedin/answer/a6269510?lang=ko-KR)라는 이름으로 제공됩니다.

MEOW는 결정적 추론의 각 단계와 중첩 없는 한 단계 가정을 화면에 순서대로
보여줍니다. 한 단계 가정으로 결론을 내지 못하면 분기 탐색으로 해 하나를
찾아 최종 보드에 표시합니다. Windows에서 pygame으로 실행하거나
웹페이지에서 바로 사용할 수 있습니다.

별도의 Exact verifier가 입력을 `UNIQUE`, `MULTIPLE`, `UNSOLVABLE`로
분류합니다. 솔버는 verifier가 찾은 해 좌표를 읽지 않습니다.

## 실행

### 홈페이지

설치 없이 [웹페이지](https://june2358.github.io/meow-puzzle-solver/)에서
바로 실행할 수 있습니다.

### pygame

- Windows 10/11
- Python 3.12.2
- pygame-ce 2.5.8
- [uv](https://docs.astral.sh/uv/)

pygame 화면은
[Pretendard v1.3.9](https://github.com/orioncactus/pretendard/releases/tag/v1.3.9)의
Regular와 SemiBold를 번들하며
[SIL Open Font License 1.1](meow/assets/fonts/OFL-Pretendard.txt)을 따릅니다.
Desktop과 Web 모두 같은 실제 weight 파일을 사용합니다.

최초 환경 준비:

```powershell
uv sync
```

실행:

```powershell
uv run python -m meow
```

전체 테스트와 정적 검사는 다음과 같이 실행합니다.

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest -q -W error
```

### 기본 프리셋

| 이름 | 크기 | 풀이 경로 |
| --- | ---: | --- |
| `쉬움` | 4×4 | 결정적 추론 |
| `보통` | 7×7 | 결정적 추론 |
| `어려움` | 11×11 | 긴 결정적 추론 |
| `전문가` | 5×5 | 한 단계 가정 |
| `마스터` | 10×10 | 한 단계 가정 |
| `극한` | 8×8 | 한 단계 가정 정체 후 분기 탐색 |

## Queens 문제 입력

JSON 붙여넣기는 다음 하나의 형식을 사용합니다.

```json
{
  "regions": [
    ["A", "A", "D", "C"],
    ["A", "A", "A", "C"],
    ["A", "A", "A", "C"],
    ["B", "B", "B", "B"]
  ]
}
```

규칙:

- `regions`는 N×N 배열입니다.
- 각 값은 빈 문자열이 아닌 영역 이름입니다.
- 서로 다른 영역은 정확히 N개여야 합니다.
- 직접 입력과 JSON 붙여넣기는 1×1부터 26×26까지 지원합니다.
- 입력 화면에서 크기를 고른 뒤 `A`~`Z`로 영역을 칠할 수 있습니다.

이미지 입력은 내장 OCR이 아닙니다. Desktop에서는 `프롬프트 복사`와
`JSON 붙여넣기`가 운영체제 클립보드를 사용하며 `Ctrl+V`도 지원합니다.
Web에서는 `프롬프트 보기`가 선택 가능한 read-only textarea를 열고,
`JSON 입력`이 실제 HTML textarea를 엽니다. 모바일에서는 이 입력칸을 길게
눌러 브라우저의 기본 붙여넣기를 사용합니다. Web 앱은 클립보드 읽기 권한을
요청하지 않습니다.

프롬프트를 이미지와 함께 비전 AI에 전달한 뒤 반환된 raw JSON을 불러옵니다.
붙여넣기가 실패하면 입력창의 텍스트와 기존 격자를 모두 보존합니다.

## 풀이 순서

```text
Exact 해 분류
  ↓
결정적 추론
  ↓ 정체
한 단계 가정
  ↓ 선택한 MRV 단위의 모든 가정 정체
분기 탐색으로 답 하나 표시
```

### 1. 결정적 추론

세부 기법은 다음 내부 단계와 사용자용 이름으로 분류합니다.

| 내부 명칭 | 사용자용 명칭 | 현재 포함 기법 |
| --- | --- | --- |
| `DIRECT_PROPAGATION` | 기본 확정 | 배치된 고양이의 충돌 제거, 행·열·영역 Single |
| `UNIT_SUPPORT` | 단위 막힘 | 한 단위의 모든 후보와 충돌하는 칸 제외 |
| `CONTAINER_MATCHING` | 묶음 잠금 | 영역↔행·열 잠금, Hall 잠금 |

아래 알고리즘 순서로 더 이상 변화가 없을 때까지 반복합니다. 한 deduction을
적용하면 다시 기본 확정부터 검사합니다.

- 배치된 고양이의 행·열·영역·인접 충돌 제거
- 행, 열, 영역 Single
- 단위 막힘
- 영역↔행/열 잠금
- Hall 잠금(최대 3개 단위)

각 `LogicStep`은 사유와 적용 내역을 분리해 저장합니다. 화면에서 새로 확정된
고양이와 X는 기존 표시와 다른 색으로 나타납니다.

### 2. 한 단계 가정

내부 명칭은 `SINGLETON_PROBING`입니다. 현재 구현은 CAT/X 양쪽을 시험하는
방식이 아니라, 선택한 단위의 각 후보를 고양이라고 한 번씩 가정합니다.

1. MRV로 후보가 가장 적은 미완성 행·열·영역 하나를 고릅니다.
2. 선택한 단위의 후보 하나에 고양이를 가정합니다.
3. 그 가정 상태에서는 결정적 추론만 실행합니다.
4. 가정이 모순이면 원본 상태에 해당 칸을 X로 반영하고 결정적 추론을
   다시 실행합니다.
5. 가정에서 해가 완성되면 그 해를 반환합니다.
6. 가정이 정체하면 원본으로 복원하고 같은 단위의 다음 후보를 시험합니다.
7. 선택한 단위의 모든 후보가 정체하면 즉시 분기 탐색으로 전환합니다.

가정 안에서 또 다른 한 단계 가정이나 분기 탐색을 시작하지 않습니다.
모순으로 X를 확정한 뒤 가정을 종료하고 새 상태에서 다시 시작하는 것은
순차적인 다음 회차입니다.

### 3. 분기 탐색

내부 명칭은 `BACKTRACK_SEARCH`입니다.

선택한 MRV 단위의 모든 후보를 한 번씩 가정해도 정체하면 다른 단위를
시험하지 않고, 임시 가정이 없는 현재 상태에서 분기 탐색을 시작합니다.
분기 탐색의 내부 경로는 풀이 화면에 재생하지 않고 첫 해 하나 또는 해
없음만 표시합니다.

## 결과

- `UNIQUE`: 표시한 해가 유일합니다.
- `MULTIPLE`: 첫 유효 해 하나를 표시하고 다른 해가 있음을 알립니다.
- `UNSOLVABLE`: 논리 모순 또는 분기 탐색 실패 후 해 없음을 표시합니다.

## 화면 조작

- `←` / `→`: 이전·다음 프레임
- 이전·다음 키나 버튼 길게 누르기: 연속 이동
- `Space`: 자동 재생·정지
- `Home` / `End`: 처음·끝
- `Esc`: Queens 문제 입력 화면

## 구조와 검증

- `main.py`: Pygbag이 요구하는 얇은 공통 앱 진입점
- `.github/workflows/pages.yml`: 웹페이지 빌드·게시 자동화
- `scripts/build_web.py`: 최소 런타임 staging과 Pygbag build
- `meow/logic_solver.py`: 결정적 추론 고정점
- `meow/solver.py`: 한 단계 가정과 분기 탐색
- `meow/exact_solver.py`: 독립 해 분류
- `meow/timeline.py`: 화면에 보여줄 선형 풀이 기록
- `meow/app.py`: 문제 입력과 풀이 재생을 잇는 앱 수명주기
- `meow/input_dialog.py`: 프리셋·직접 입력·JSON/이미지 전사 입력
- `meow/web_text_dialog.py`: Web 전용 일회성 DOM textarea
- `meow/runtime.py`: Desktop/Web 공통 frame pacing
- `meow/visualizer.py`: pygame-ce 보드와 재생 UI
- `meow/ui_style.py`, `meow/ui_components.py`: 두 화면이 공유하는 UI 기반
- `meow/assets/fonts/`: 번들 한글 폰트와 OFL
- `meow/puzzles.json`: 패키지에 포함된 여섯 기본 프리셋
- `tests/`: 풀이·입력·화면의 핵심 회귀 검증
