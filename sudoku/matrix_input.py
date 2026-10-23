"""External AI/OCR transcription instructions for Sudoku matrices."""

OCR_MATRIX_PROMPT = """Transcribe the Sudoku puzzle in the attached image.

Rules:
1. Do not solve the puzzle or infer any missing digit.
2. Read cells from top to bottom and left to right.
3. Copy only clearly visible fixed/given digits.
4. Use 0 for every blank or unreadable cell.
5. Ignore pencil marks, candidate notes, highlights, and surrounding text.
6. Return exactly one 9x9 JSON array of integers from 0 to 9.
7. Return raw JSON only: no explanation, Markdown code fence, or object wrapper.

The following example demonstrates the output format only. Do not copy its
digits unless they are actually visible in the attached image.

Example visible grid:
53..7....
6..195...
.98....6.
8...6...3
4..8.3..1
7...2...6
.6....28.
...419..5
....8..79

Required example output:
[
  [5, 3, 0, 0, 7, 0, 0, 0, 0],
  [6, 0, 0, 1, 9, 5, 0, 0, 0],
  [0, 9, 8, 0, 0, 0, 0, 6, 0],
  [8, 0, 0, 0, 6, 0, 0, 0, 3],
  [4, 0, 0, 8, 0, 3, 0, 0, 1],
  [7, 0, 0, 0, 2, 0, 0, 0, 6],
  [0, 6, 0, 0, 0, 0, 2, 8, 0],
  [0, 0, 0, 4, 1, 9, 0, 0, 5],
  [0, 0, 0, 0, 8, 0, 0, 7, 9]
]"""
