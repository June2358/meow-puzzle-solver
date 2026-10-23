# Unified Puzzle Engine Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or executing-plans. Each owner verifies RED/GREEN, then independently review the whole change.

**Goal:** 두 솔버가 같은 실행 엔진과 전달 계약에 규칙을 제공하도록 재구성한다.
**Architecture:** 공통 Engine과 구조적 State/Domain 계약, 불변 실행 기록, PuzzlePlugin 앱 등록.
**Tech Stack:** 기존 Python3.12, pygame-ce, pytest, Ruff, Pygbag, uv. 새 의존성 없음.
**Spec:** docs/superpowers/specs/2026-10-24-unified-engine-design.md

## Global Constraints

퍼즐 기법과 순위/적용 순서, 설명, 대표 해/해 분류, 원본 초안과 종료 정리를 보존한다.
공통 코드에 퍼즐 import/이름 분기 없음. 선택된 패키지만 웹에 포함한다. 원본/GitHub 변경 없음.

## Review Focus

이미 완성된 상태의 마지막 추론, 빈 가정 라운드, 반증 재시작, 원본/가정 상태 분리,
H1 정체 이력, 해 중복과 두 번째 해 검사, 조용한 탐색의 기록 오염을 검사한다.

## Task 1 — Engine (common owner)

Files: puzzle_common/engine.py, tests/common/test_engine.py.
Interfaces: LogicStatus(SOLVED/STALLED/CONTRADICTION); LogicStep(before,after,deduction);
LogicRun(status,initial_state,final_state,steps,contradiction); ProbeRun(assumption,logic_result);
ProbeRound(before,candidates,probes,elimination); SolveRun(initial_logic_result,probing_rounds,solutions,used_backtrack_search).
Engine(domain).propagate(state,record=True), .solve(state,solution_limit).

- [x] RED: 작은 가짜 퍼즐로 논리/가정/반증/탐색·해 중복/상한/기록 순서 검사를 작성하고 실패 확인.
- [x] GREEN: 실제 실행 루프와 기록을 공통 엔진에 구현하고 집중 검사/Ruff 통과.

## Task 2 — MEOW (MEOW owner)

Files: meow/solver.py, logic_solver.py, state.py, engine_adapter.py; tests/meow 관련 검사.
Consumes Task1. 제공할 규칙: 기존 기법/순위/MRV/가정·반증·검증·해 좌표 기준.
독립 exact 검증 전후와 기존 공개 결과/LogicResult 변환을 유지한다.

- [x] RED: solve/solve_logically의 공유 엔진 사용과 입력 상태 격리 검사.
- [x] GREEN: 퍼즐별 고정점·가정·재귀 루프 삭제, 기존 검사와 기록 비교.

## Task 3 — Sudoku (Sudoku owner)

Files: sudoku/solver.py, solver_state.py, engine_adapter.py; tests/sudoku 관련 검사.
Consumes Task1. 제공할 규칙: 기존 기법/적용/H1·이력/MRV/가정·반증/해 grid 기준.
같은 실행 기록을 기존 SolveStep 순서와 메시지로 변환하고 해2개까지 확인한다.

- [x] RED: 공유 엔진 사용 및 기존 step/유일성/배치 검사.
- [x] GREEN: 별도 고정점·가정·DFS 루프 삭제, 기존 검사와 기록 비교.

## Task 4 — App registration (root)

Files: common/app.py, both app.py, four entrypoints, common/app tests, both app_flow tests, web fixture.
PuzzlePlugin의 네 callable로 등록하고 run_app(plugin)만 앱 흐름을 실행한다.

- [x] RED: 플러그인 계약/같은 결과 전달/해 없음 재입력/예외 종료 검사를 실패 확인.
- [x] GREEN: 등록 데이터와 진입점을 갱신하고 기존 화면 계약을 유지한다.

## Task 5 — Integration (root/reviewer)

- [x] 변경 전51개 전체 결과/기록 지문과 전체370/1 검사 저장.
- [x] 51개 전체 기록 일치, 전체 검사/Ruff/실제 두 웹 빌드와 브라우저 확인.
- [x] 모든 어댑터와 엔진 경계를 독립 검토하고 문서/실제 수치 갱신.
- [x] 깨끗한 로컬 브랜치에 커밋.
