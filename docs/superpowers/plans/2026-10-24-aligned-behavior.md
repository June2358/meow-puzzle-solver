# Aligned Behavior Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or executing-plans. Complete each task's RED/GREEN check and independently review the final change.

**Goal:** 알고리즘/고유 편집을 유지하고 두 앱의 공통 동작과 UI 데이터 전달을 일치시킨다.
**Architecture:** 순수 PlaybackData 계약, 앱별 to_playback 변환, 공통 결과 정책과 typed frame 재생. 배치/작은 글꼴도 공유한다.
**Tech Stack:** 기존 Python3.12.2, pygame-ce, pytest, Ruff, Pygbag, uv.
**Spec:** docs/superpowers/specs/2026-10-24-aligned-behavior-design.md

## Global Constraints

솔버/모델/타임라인/파서/프리셋 계약 변경 없음. 새 의존성 없음. GitHub 게시 없음.
공통 모듈의 퍼즐 import/앱 이름 분기 없음. 기존 모달 정리와 입력 보존을 유지한다.

## Review Focus

해 없음은 원본 초안과 같은 메시지로 양쪽 편집기에 복귀한다.
빈 단계/다른 퍼즐의 결과/다른 퍼즐의 Frame은 명확한 오류로 거부한다.
같은 Frame이 보드와 패널에 전달되고 처음/끝/누르기/자동 재생이 기존과 같다.
수정키가 삭제/입력/시작으로 전달되지 않고 MEOW 크기 필드와 실제 영역 입력은 동작한다.
배지/활성 가정/설명/효과/도움말은 실제 프리셋에서 겹치지 않는다.

## Task 1: Result contract, layout, and application outcome

Files: create puzzle_common/presentation.py, puzzle_common/layout.py, both app presentation.py;
modify common/app.py, both app.py, common/ui_style.py info font;
tests/common/test_presentation.py, test_layout.py, test_app.py, both test_app_flow.py, font tests.

Interfaces: Outcome; PlaybackData[Frame](outcome,frames); to_playback(result);
BoardLayout(cell_size,board_rect,panel_rect,window_size); get_board_layout(size);
Fonts.info. Layout constants as spec. run_app solver/player use PlaybackData and no per-app error callback.

- [x] Write RED tests for normalized real unique/multiple/none cases, empty frames, shared outcome retry, layout and info role.
- [x] Implement pure result adapters and common outcome policy; consume shared error contract in app callbacks.
- [x] Run task tests GREEN, verify no algorithm/model changes.

## Task 2: Playback consumes common data and geometry

Files: common/playback.py, both visualizer.py, tests/test_playback.py, both test_visualizer.py.
Consume Task1 interfaces; do not edit Task1-owned files. Constructors accept PlaybackData of their typed Frame.
Shared class is PlaybackScreen[Draft,Frame], receives data, edit_draft, board_size, caption, fonts.
Base owns frames/current_frame/frame_count/outcome, shared geometry and generic title.
Hooks _draw_board(frame), _presentation(frame). Remove PlaybackDetails.status and per-app status/geometry policy.
Use generic get_board_layout, shared coordinates and cell helpers, preserve puzzle rendering.
No compatibility layers for old raw-result constructor; update all actual visualizer callers/tests to to_playback.

- [x] Write RED paired tests for normalized-data constructors, shared layout/badges and exact current-frame delivery.
- [x] Implement shared ownership and update real adapters/callers; keep trace/board semantics intact.
- [x] Run both visualizer/control regressions GREEN; render all built-in trace frames and inspect dense panels.

## Task 3: Input behavior and information typography

Files: common/input_dialog.py, both input_dialog.py, tests/test_common_input_dialog.py,
both input tests, both web dialog tests if geometry assertions need updating. No app.py edits.
Consume Task1 get_board_layout/Fonts.info; MEOW constructor accepts initial_error and forwards it.
Common base receives board_size; owns common layout and directional/linear navigation.
Move MEOW _move_linear logic into base and preserve focused size-field interception.
Guard Ctrl/Alt/GUI keys after Ctrl+V/escape handling; do not change Sudoku plain C/R/S or MEOW alphabet meaning.

- [x] Write RED paired tests for initial arrows/Tab/Shift+Tab, layout/info font, modifier guards and no-op feedback preservation.
- [x] Implement common behavior; update callers and instructions with Tab; retain domain edit behavior.
- [x] Run input/DOM regressions GREEN including size field and drag release.

## Task 4: Integrate, review, verify and document

- [x] Review task changes, run Ruff/format/full pytest and correct material regressions.
- [x] Build both real Pygbag bundles, inspect contents, verify both apps in actual browser.
- [x] Independently review complete diff and verify algorithm/schema files unchanged from ee96e80.
- [x] Update architecture/verification docs, commit clean local branch.
