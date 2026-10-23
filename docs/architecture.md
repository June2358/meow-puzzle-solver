# 공통 구현과 퍼즐 어댑터

두 앱은 하나의 입력 화면과 하나의 풀이 재생 화면을 사용한다.
공통 모듈은 `meow`, `sudoku`를 import하지 않으며 앱 이름으로 분기하지 않는다.

| 공통 구현 | 책임 | 퍼즐별로 제공할 내용 |
| --- | --- | --- |
| `puzzle_common.app.run_app` | pygame 수명주기, 편집 → 풀이 → 재생 → 편집 반복, 해 없음의 편집 복귀, 종료 정리 | 편집기/재생기 생성, 정규화된 solve, 초안 추출 |
| `puzzle_common.presentation.PlaybackData` | 공통 해 분류와 비어 있지 않은 불변 단계 목록 | `meow.presentation.to_playback`, `sudoku.presentation.to_playback`이 기존 결과를 변환 |
| `puzzle_common.layout` | 입력/재생 창·보드·패널의 배치, `cell_rect`/`cell_at` 셀 좌표와 히트 검사 | 실제 격자 크기 |
| `puzzle_common.constraints.locked_candidate_targets` | 후보가 한 단위에 모였을 때 원본 단위 밖에서 제거할 칸 선택 | 단위/후보/가능 칸 판정, 기법 순서, 최소 근거 수와 설명 |
| `puzzle_common.input_dialog.InputDialog` | 레이아웃, 버튼, 프리셋 조작, 메시지/사용법, JSON/프롬프트/클립보드, 모달 정리, 이벤트 루프 | 제목/설명/프롬프트, 보드 상태와 편집 규칙, 파서/검증, 보드 그리기 |
| `puzzle_common.playback.PlaybackScreen` | 현재 단계와 인덱스, 공통 결과 배지·셀 위치·좌표·패널·버튼, 이동/누르기 반복/자동 재생/포커스 해제, 이벤트 루프 | 전달받은 같은 단계의 보드 그리기와 `PlaybackDetails` 변환 |
| `puzzle_common.catalog.read_catalog` | 패키지 JSON 파일 읽기와 파일/JSON 오류 처리 | 프리셋 스키마 검증과 캐시 |
| `puzzle_common.json_input.decode_json` | 입력과 프리셋 JSON 디코딩, 구문/과도한 복잡도 오류 처리 | 실제 숫자/영역 JSON 스키마 검증과 앱별 오류 타입 |
| 그 외 `puzzle_common` | 폰트/색상/텍스트 줄바꿈/격자선, 좌표 이름, 버튼/패널, 클립보드, DOM textarea, 프레임 처리 | 실제로 다른 폰트 크기와 퍼즐 영역 경계 |

## 입력 화면

`MeowInputDialog`, `SudokuInputDialog`는 공통 `InputDialog`를 상속한다.
앱별 `input_dialog.py`에는 숫자 또는 영역의 입력 규칙, JSON을 실제 초안으로
적용하는 로직, 보드 그리기만 둔다. MEOW의 크기 입력·영역 드래그와 Sudoku의
숫자 입력·중복 표시는 각각의 퍼즐 입력 규칙이다.

잘못된 JSON은 현재 보드와 입력문을 보존한다. 모달이 열려 있는 동안에는
뒤의 보드를 편집하지 않는다. 모달 생성·폴링·오류 표시·닫기와 예외 정리는
공통 화면이 담당한다.

첫 방향키와 Tab은 양쪽에서 첫 칸을 선택한다. Tab/Shift+Tab은 칸 순서로
이동하고 양 끝에서 멈춘다. Ctrl/Alt/GUI 조합은 편집·삭제·풀이 시작으로
전달하지 않으며 기존 Ctrl+V JSON 기능은 유지한다. MEOW 크기 필드는 먼저
키를 처리한다. A~Z 영역 입력과 Sudoku 단독 C/R/S 단축키는 고유 동작으로 유지한다.
같은 값을 다시 입력하면 기존 오류/안내를 유지한다.

## 풀이 재생

`MeowVisualizer`, `SudokuVisualizer`는 공통 `PlaybackScreen`을 상속한다.
알고리즘 결과의 자료형은 각자 유지한다. UI에 전달하기 전에 `to_playback()`이
`PlaybackData(outcome, frames)`로 변환한다. 해 분류는 `UNIQUE`, `MULTIPLE`,
`UNSOLVABLE`로 통일한다. Sudoku는 기존 steps tuple을 그대로 쓰고, MEOW는
기존 build_timeline의 결과를 사용한다. 보드 상태와 추론 근거를 다른 자료형으로 복제하지 않는다.

`PlaybackScreen[Draft, Frame]`이 현재 단계를 한 번 읽어 `_draw_board(frame)`과
`_presentation(frame)`에 같은 객체로 전달한다. 후자는 제목·사유·적용 내역·활성 가정·
관련 영역 색상을 `PlaybackDetails`로 변환한다. 해 분류 배지는 공통 화면이 표시한다.
Visualizers는 원본 SolveResult 대신 각 퍼즐의 typed frame을 담은 PlaybackData를 받는다.

해가 없으면 두 앱 모두 원본 초안을 보존해 편집 화면으로 복귀한다.
공통 메시지는 `현재 입력으로 가능한 해가 없습니다. 원본 문제와 입력을 확인하세요.`이다.
직접 생성한 해 없음 재생 데이터도 양쪽 재생기에서 확인할 수 있다.

고양이/X/색상 영역과 숫자/후보/근거 강조의 렌더링은 보드 어댑터에 남긴다.
이전/다음, Home/End, 키와 마우스 길게 누르기, 자동 재생, Esc 편집 복귀와
종료 처리는 공통 화면에서 한 번만 구현한다.

창은 양쪽 입력/재생 모두 1010×700, 보드 영역540, 패널350×560을 사용한다.
작은 안내 글꼴은 공통 `Fonts.info`15이며 실제 숫자/후보 크기는 각 퍼즐에 맞게 유지한다.

## 변경 기준

Sudoku의 pointing/claiming과 MEOW의 영역↔행/열 잠금은 같은 후보 고정 연산을 사용한다.
실제 배치/제외 적용과 풀이 기록은 각 솔버에 남긴다. MEOW의 모순 판정과 메시지는
`LogicSnapshot.contradiction_message()`가 담당한다. 버튼은 그릴 때 호버를 계산하며
입력/재생 화면이 별도의 호버 상태를 갱신하지 않는다.

버튼·패널·조작·메시지·입력창·앱 전환을 바꿀 때에는 공통 모듈을 수정한다.
퍼즐 규칙·풀이 순서·JSON 형식·숫자 또는 영역의 의미를 바꿀 때에는 해당
퍼즐의 코드와 어댑터를 수정한다. 공통 모듈에서 앱 이름을 검사하는 방식으로
예외를 쌓지 않는다.

검사는 `uv run python -m pytest -q -W error`로 양쪽 앱과 공통 회귀 검사를
함께 실행한다. 웹 배포 전에는 `uv run --group web python scripts/build_web.py`로
두 번들을 함께 빌드한다.
