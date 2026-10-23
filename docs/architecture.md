# 공통 구현과 퍼즐 어댑터

두 앱은 하나의 입력 화면과 하나의 풀이 재생 화면을 사용한다.
공통 모듈은 `meow`, `sudoku`를 import하지 않으며 앱 이름으로 분기하지 않는다.

| 공통 구현 | 책임 | 퍼즐별로 제공할 내용 |
| --- | --- | --- |
| `puzzle_common.app.run_app` | pygame 수명주기, 편집 → 풀이 → 재생 → 편집 반복, 오류와 종료 정리 | 편집기/재생기 생성, solve, 초안 추출과 표시할 수 없는 결과의 오류 |
| `puzzle_common.input_dialog.InputDialog` | 레이아웃, 버튼, 프리셋 조작, 메시지/사용법, JSON/프롬프트/클립보드, 모달 정리, 이벤트 루프 | 제목/설명/프롬프트, 보드 상태와 편집 규칙, 파서/검증, 보드 그리기 |
| `puzzle_common.playback.PlaybackScreen` | 패널과 버튼, 단계 이동/누르기 반복/자동 재생/포커스 해제, 텍스트/효과/색상 칩 렌더링, 이벤트 루프 | 보드 그리기와 알고리즘 기록을 `PlaybackDetails`로 변환 |
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

## 풀이 재생

`MeowVisualizer`, `SudokuVisualizer`는 공통 `PlaybackScreen`을 상속한다.
알고리즘 결과의 자료형은 각자 유지한다. 어댑터의 `_presentation()`이 현재
단계를 제목·사유·적용 내역·상태·활성 가정·관련 영역 색상으로 바꿔
`PlaybackDetails`를 반환하고, 공통 화면이 이를 표시한다.

고양이/X/색상 영역과 숫자/후보/근거 강조의 렌더링은 보드 어댑터에 남긴다.
이전/다음, Home/End, 키와 마우스 길게 누르기, 자동 재생, Esc 편집 복귀와
종료 처리는 공통 화면에서 한 번만 구현한다.

## 변경 기준

버튼·패널·조작·메시지·입력창·앱 전환을 바꿀 때에는 공통 모듈을 수정한다.
퍼즐 규칙·풀이 순서·JSON 형식·숫자 또는 영역의 의미를 바꿀 때에는 해당
퍼즐의 코드와 어댑터를 수정한다. 공통 모듈에서 앱 이름을 검사하는 방식으로
예외를 쌓지 않는다.

검사는 `uv run python -m pytest -q -W error`로 양쪽 앱과 공통 회귀 검사를
함께 실행한다. 웹 배포 전에는 `uv run --group web python scripts/build_web.py`로
두 번들을 함께 빌드한다.
