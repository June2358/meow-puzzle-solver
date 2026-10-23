# 공통 결과와 재생 기록

사용자가 승인한 다음 작업은 기존 퍼즐별 결과/기록 형식으로 되돌리는 변환층을 없애는 것이다.
기준 d6bc18d의 알고리즘 순서·해 분류·대표 해·설명과 보드 표현을 유지한다.

`engine.SolveResult(outcome, run)` 하나가 양쪽 솔버의 반환값이며 화면까지 같은 객체를 넘긴다.
Outcome은 독립 검증으로 얻은 분류다. MEOW는 exact 판정을 유지하고 Sudoku는 해2개까지
찾은 결과로 분류한다. 해1개를 찾았다는 이유로 공통 엔진이 유일해라고 추정하지 않는다.

`LogicRun`, `LogicStep`, `ProbeRun`, `ProbeRound`, `SolveRun`은 원본을 그대로 사용한다.
MEOW의 LogicResult/LogicStep/LogicStatus/ProbeResult/ProbingRound/SolveOutcome/SolveResult,
Sudoku의 SolveStatus/StepKind/SolveStep/SolveResult와 변환 함수/호환 별칭을 제거한다.
도메인 기법·추론·결정·모순 근거와 그 검증은 유지한다.

`presentation.build_frames(result)`가 공통 PlaybackFrame으로 한 번만 순회한다.
프레임은 kind/snapshot/deduction/assumption/status/contradiction/candidates/probe_index를 담고,
RESTORE/REFUTATION의 assumption은 비활성이다. 보드/추론/근거를 다시 복제하지 않는다.

일정한 단계 순서는 START → 초기 추론 → LOGIC_END → 각 라운드의 후보 선택 →
가정 시작/추론/종료/실패 시 복원 → 반증·재추론·LOGIC_END → 필요 시 SEARCH → FINAL이다.
이전 Sudoku가 생략하던 선택/종료/복원과 MEOW 반증 이후 종료 표시가 추가될 수 있다.
이 차이는 사용자에게 사전에 알렸으며 실제 알고리즘과 기존 설명을 바꾸지 않는다.

별도 PlaybackData/to_playback도 제거한다. PlaybackScreen은 같은 SolveResult에서 프레임을
한 번 만들고, 화면 구성 전에 퍼즐별 `_validate_frames()`를 호출한다. 같은 공통 프레임이라도
다른 퍼즐의 스냅샷을 거부한다. MEOW는 모든 스냅샷의 영역 소속, Sudoku는 스냅샷 구조와
초기 보드 소속을 확인한다. 퍼즐별 presentation은 describe_frame(frame,result)만 제공한다.

검증 기준은 변경 전51건의 공통 엔진 원본 기록·분류·대표 해가 정확히 같고, 기존 화면999개의
내용과 보드 픽셀이 새 단계 목록에 같은 순서로 남아 있는 것이다. 새 공통 단계만 추가될 수 있다.
변경 전 전체391 passed/1 skipped. 공통 계약·순서·비활성 반증/복원·원본 최종 상태 검사,
전체 검사/Ruff/실제 웹 빌드·브라우저·독립 검토를 수행한다. 새 의존성/원본/원격 변경 없음.
