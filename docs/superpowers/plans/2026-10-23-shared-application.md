# Shared Application Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Track steps below.

**Goal:** 공통 입력/재생/앱 흐름을 사용하고 앱에는 퍼즐별 로직과 표현 어댑터만 남긴다.
**Architecture:** `puzzle_common.input_dialog`, `puzzle_common.playback`, `puzzle_common.app`의 공통 구현과 퍼즐별 작은 하위 클래스/콜백. 공통 모듈은 퍼즐 패키지를 import하지 않는다.
**Tech Stack:** 기존 Python 3.12.2, pygame-ce, uv, pytest, Ruff, Pygbag만 사용.
**Spec:** `docs/superpowers/specs/2026-10-23-shared-application-design.md`

## Global Constraints

솔버/모델/입력 계약과 기존 주요 기능을 유지한다. 공통 코드에 앱 이름 분기를 넣지 않는다. 새 의존성/원격 게시/원본 저장소 변경 없음. 단일 공통 코드에 실제 양쪽 호출자를 연결한다.

## Review Focus

- MEOW 크기 편집·드래그·색상 칩과 Sudoku 숫자·충돌·후보 렌더링 보존.
- JSON 창의 오류/부분 생성/종료 정리 및 입력문·원본 유지.
- 키 반복, 좌우 동시 누름/해제, 마우스 길게 누르기, 포커스 해제와 자동 재생 종료.
- 풀 수 없는 입력의 편집 복귀와 예외 시 pygame 정리.
- 두 앱의 브라우저 번들에 새 공통 모듈 포함.

## Task 1: Shared input screen

Own `puzzle_common/input_dialog.py`, app `input_dialog.py`, associated input tests. Consume `puzzle_common.ui_components.draw_panel(screen, rect)` and existing fonts/clipboard/DOM. Keep constructor APIs and real puzzle-specific validation. Extract layout/buttons/panel/messages/instructions/event loop/clipboard+web lifecycle fully. Add shared behavior tests first, observe red; implement; run both input regression suites.

- [x] Implement shared input screen and thin adapters, preserve direct edit/paste behavior.

## Task 2: Shared playback screen

Own `puzzle_common/playback.py` (and presentation helper if needed), app `visualizer.py`, playback tests. Consume same `draw_panel` helper and existing fonts/runtime. Share complete frame navigation/autoplay/event/run/panel/control rendering. App code supplies semantic presentation data and puzzle board rendering; no duplicated generic playback methods. Add common control behavior tests first; preserve all prior board/trace checks.

- [x] Implement common playback with both app adapters and run both visualizer suites.

## Task 3: Shared lifecycle and remaining infrastructure

Own `puzzle_common/app.py`, both `app.py`, app-flow tests, catalog loading, shared drawing helper, docs. Start from retained app-flow tests; add common cleanup/edit/error tests before implementation. Consolidate preset asset file loading with existing validation callbacks. Audit remaining non-domain duplicates after Tasks1/2 return and merge real remaining overlap.

- [x] Share application lifecycle and preset file IO, update docs and audit remaining duplication.

## Task 4: Verify and review

- [x] Full Ruff/format/pytest and actual dual Pygbag build + bundle inspection.
- [x] Real browser input/solver/playback/error/edit checks for both apps.
- [x] Independent review of entire change and fix material findings.
- [x] Compare lines to previous integration and original sum; verify original repositories/domain logic unchanged; commit clean branch.
