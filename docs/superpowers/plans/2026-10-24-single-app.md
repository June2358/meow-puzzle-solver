# Single Puzzle App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Each task owns disjoint files; root integrates and verifies.

**Goal:** One app/editor/player/renderer/web bundle with two puzzle definitions.
**Architecture:** Existing solver records remain authoritative; pure domain projections feed common display data.
**Tech Stack:** Python 3.12.15, pygame-ce 2.5.8, Pygbag 0.9.3; no new dependencies.
**Spec:** docs/superpowers/specs/2026-10-24-single-app-design.md

## Global Constraints

- Preserve solver rules, order, independent solution classification and invalid-input safety.
- Puzzle packages contain no screen/event/drawing implementation.
- Keep one canonical timeline and one runtime/bundle. Preserve existing web entry links.
- Do not modify shared main or deploy while implementing this branch.

## Review Focus

- Invalid/complex JSON preserves drafts; switching modes preserves separate drafts.
- Foreign snapshots rejected before display; displayed outcome stays certified.
- Closing a modal/app cannot restart input; Escape navigation remains unambiguous.
- Removed candidates, evidence, active/refuted assumptions and large Queens grids remain visible.
- Compatibility URLs load the right mode from the same single APK.

### Task 1: Display and puzzle contract (root)
- [x] Add tested immutable view types and explicit puzzle definition callbacks.
- [x] Validate shape, marks and geometry at the display boundary.

### Task 2: Renderer and domain definitions (implementer A)
- [x] Replace puzzle drawing/screens with common board renderer and pure domain projections.
- [x] Preserve native frame validation and all domain display meaning.
- [x] Run focused domain/display tests and report code removed.

### Task 3: Common editor (implementer B)
- [x] One editor consumes PuzzleDefinition and immutable normalized grid buffers.
- [x] Cover keyboard, mouse painting, size bounds, presets, malformed JSON, quit/modal safety.
- [x] Replace old editor-specific tests with tests of both real definitions.

### Task 4: One application and build (implementer C)
- [x] One in-app selector/lifecycle and one main entry point; one build with both packages.
- [x] Keep previous CLI/URL entry points as small entry adapters only where used.
- [x] Update build/app tests, launcher and README.

### Task 5: Integrate playback and validate (root)
- [x] Common player uses domain projections and common renderer; remove legacy visualizers.
- [x] Migrate view tests, retain native algorithm/parser/trace regression coverage.
- [x] Ruff, full pytest, one web build, browser checks for both modes, independent review.
- [x] Commit reviewed branch and present result without changing shared main.
