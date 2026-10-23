# Puzzle Solvers Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 두 앱을 하나의 저장소와 공통 기반으로 통합하면서 기존 동작을 유지한다.
**Architecture:** 루트의 `meow`, `sudoku`는 퍼즐별 패키지, `puzzle_common`은 실제 공유 코드다. 웹은 앱별로 별도 번들을 만들고 한 사이트에 게시한다.
**Tech Stack:** Python 3.12.2, pygame-ce 2.5.8, pytest 9.1.1, ruff 0.16.4, pygbag 0.9.2, uv, GitHub Pages.
**Spec:** `docs/superpowers/specs/2026-10-23-unification-design.md`

## Global Constraints

기능·솔버·입력 정책과 화면을 유지한다. 기존 두 저장소를 수정하지 않는다. 신규 의존성과 원격 게시를 추가하지 않는다. 공통 폰트 라이선스를 보존한다.

## Review Focus

- 공통 코드가 빠진 웹 번들은 브라우저에서 import에 실패한다: 번들 내용을 검사하고 실제 두 앱을 연다.
- 폰트 위치 변경 시 한글/굵기/앱별 크기가 깨질 수 있다: 기존 폰트 검사와 브라우저 화면을 확인한다.
- 중복 테스트 모듈 이름이 회귀 검사를 누락시킬 수 있다: 전체 수집 수와 두 앱 검사를 확인한다.
- 브라우저 JSON/프롬프트의 한글과 오류 처리 보존: 기존 DOM 및 입력 테스트를 유지한다.
- 빌드 정리 작업이 프로젝트 파일을 지우면 안 된다: 경로 경계 및 누락 산출물 검사를 유지한다.

## Task 1: Repository and shared environment

Files: root `pyproject.toml`, `uv.lock`, `README.md`, `tests/conftest.py`, `docs/*`, `.github/workflows/*`.
Interfaces: app package names stay `meow`, `sudoku`; shared package name is `puzzle_common`; web entrypoints are `main_meow.py`, `main_sudoku.py`.

- [x] Preserve both source histories and move app/tests into one repository.
- [x] Unify uv, pytest and workflows; run the existing suite as a regression baseline.
- [x] Update application documentation, source links and usage commands.

## Task 2: Shared pygame infrastructure

Files: `puzzle_common/*`, app UI/runtime/clipboard/browser adapters and consumers, associated app regression tests.
Interfaces: identical Button/frame/clipboard behavior; preserve app-specific font sizes and JSON instructions; one copy of font assets in `puzzle_common/assets/fonts`.

- [x] Add a small shared-use contract test and observe it fail before extraction.
- [x] Extract existing implementations, retaining error handling and app differences.
- [x] Update all consumers and tests; run app suites and Ruff.

## Task 3: One web build and site

Files: `scripts/build_web.py`, `tests/test_web_build.py`.
Interfaces: no-argument `build_web()` builds both apps; `python scripts/build_web.py` generates `build/web/index.html`, `meow/`, `sudoku/`.

- [x] Adapt build tests first to exercise both apps, shared assets, output separation and safe deletion; observe failure.
- [x] Implement minimal multi-app staging/building and a static selection page.
- [x] Run tests, both real Pygbag builds, inspect bundles and browser behavior.

## Task 4: Review and finish

- [x] Run whole-repository Ruff, format and pytest commands.
- [x] Obtain an independent review and address material findings with regression checks.
- [x] Verify unchanged originals, preserved history, and clean committed integration branch.
- [x] Record final evidence and local launch commands; leave publication for a later request.
