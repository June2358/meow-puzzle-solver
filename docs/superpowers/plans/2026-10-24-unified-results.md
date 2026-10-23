# Unified Results Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or executing-plans. Observe RED/GREEN and independently review the complete change.

**Goal:** 하나의 결과/실행 기록을 그대로 화면까지 전달하고 과거 결과형 변환을 제거한다.
**Architecture:** 공통 SolveResult + 공통 PlaybackFrame/단일 순회, 고유 설명·보드 어댑터.
**Tech Stack:** 기존 Python3.12/pygame-ce/pytest/Ruff/Pygbag. 새 의존성 없음.
**Spec:** docs/superpowers/specs/2026-10-24-unified-results-design.md

## Global Constraints

알고리즘·기법/가정 순서·H1 이력·exact 독립 검증·대표 해·기존 화면 설명과 강조를 유지한다.
호환 별칭/옛 결과 복제 없음. 공통 코드의 퍼즐 import/이름 분기 없음. 원본/원격 수정 없음.

## Review Focus

공통 결과가 해 상한1을 유일성으로 오인하지 않아야 한다. 반증 결정은 유지하되 비활성이다.
최종 해 없음/탐색 화면은 버린 가정이 아닌 원본 상태를 쓴다. 같은 프레임형에 다른 퍼즐의
스냅샷이 있어도 화면 구성 전에 거부한다. 추가 단계가 기존 설명을 대체하거나 누락하지 않는다.

## Task 1 — Common result/frame (common owner)

Files: common/engine.py, common/presentation.py, tests/common/test_presentation.py.
Outcome + SolveResult(outcome,run), .solution/.root_state. 기존 Engine 실행 코드는 변경하지 않는다.
FrameKind10개와 PlaybackFrame, build_frames(result). 옛 PlaybackData/to_playback 제거.

- [x] RED: 분류/존재 검증, 같은 참조, 전체 단계 순서, 비활성 결정, 원본 최종 상태 검사.
- [x] GREEN: 공통 계약/순회 구현과 집중 검사/Ruff.

## Task 2 — MEOW (MEOW owner)

Files: meow solver/logic_solver/engine_adapter/solve_types/presentation/visualizer/app, tests/meow.
Consumes Task1; 공통 결과 직접 반환. 옛 결과형·logic_result_from·timeline.py 삭제.
고유 문구/효과/영역·보드 렌더링과 독립 exact 교차 검증 유지.

- [x] RED: 공통 결과·직접 LogicRun·기법/해/기록/화면 의미 검사.
- [x] GREEN: 모든 MEOW 호출자/검사 이관, 고유 변환층과 별칭 삭제.

## Task 3 — Sudoku (Sudoku owner)

Files: sudoku solver/solve_types/presentation/visualizer/app, tests/sudoku.
Consumes Task1; 공통 결과 직접 반환. 옛 결과/Step 형식·상태 enum 삭제.
고유 설명/Last Digit/후보 제거/색상 레이어와 이력·해2개 확인 유지.

- [x] RED: 공통 결과·원본 실행 기록·반증/가정·재생 의미 검사.
- [x] GREEN: 모든 Sudoku 호출자/검사 이관, 기존 단계 변환 삭제.

## Task 4 — Shared UI/app (root)

Files: common/playback.py, common/app.py, tests/test_playback.py, common app/plugin tests.
PlaybackScreen[Draft,Snapshot,Deduction,Decision,Witness]는 result를 받고 프레임을 한 번 만든다.
프레임 준비 후 `_validate_frames()`를 호출하고 화면을 구성한다. PuzzlePlugin은 같은
SolveResult를 solver→player에 전달한다.

- [x] RED: 결과 동일 객체, 같은 현재 프레임 전달, 외래 스냅샷 거부, 조작·복귀·예외 정리.
- [x] GREEN: 옛 데이터/변환 호출을 모두 갱신하고 기존 조작 검사 통과.

## Task 5 — Integration (root/reviewer)

- [x] 변경 전51개 공통 엔진 기록/분류/해와 기존999개 화면 내용·픽셀, 전체391/1 저장.
- [x] 새 구조의 동일 의미와 기존 화면 순서/내용 보존, 전체/Ruff/두 웹 빌드·브라우저 확인.
- [x] 독립 전체 검토, 실제 수치/구조 문서 갱신, 깨끗한 로컬 커밋.

실행 결과와 범위는 `docs/unified-results-verification.md`에 기록했다.
