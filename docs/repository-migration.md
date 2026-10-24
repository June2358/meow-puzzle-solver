# 공식 통합 저장소 이전

2026-10-24에 기존 `June2358/meow-puzzle-solver`를
`June2358/puzzle-solvers`로 변경하고 두 퍼즐의 공식 개발 장소로 사용한다.
기존 MEOW와 Sudoku의 커밋은 재작성하지 않고 병합 이력으로 보존한다.

통합본 `af1edf6` 이후 원본 저장소에 추가된 MEOW `f0495b2`와
Sudoku `5b4743d`의 이력도 포함한다. 해당 변경의 입력 종료 처리,
웹 런타임 사전 로딩, 숫자패드 입력, 숨은 부분집합 후보 가지치기,
풀이 완료 조기 반환, 한글 안내와 Python 환경을 공통 구조에 반영한다.
이미 공통 엔진에 포함된 로직은 중복으로 되살리지 않는다.

공식 웹 주소:

- 선택 화면: <https://june2358.github.io/puzzle-solvers/>
- MEOW: <https://june2358.github.io/puzzle-solvers/meow/>
- Sudoku: <https://june2358.github.io/puzzle-solvers/sudoku/>

기존 `simple-sudoku-solver`는 원본 코드를 보관하고 README와 웹 실행
주소에서 통합본을 안내한다. 기존 Git 이력은 양쪽 저장소에 남는다.

GitHub는 이름을 바꾼 저장소 주소를 새 주소로 연결하지만 GitHub Pages의
기존 `/meow-puzzle-solver/` 주소는 자동 연결하지 않는다. 기존 이름으로
새 저장소를 만들면 저장소 주소의 자동 연결까지 끊기므로 재사용하지 않는다.

배포는 통합 테스트와 양쪽 웹 빌드가 모두 성공한 뒤 진행한다.

게시 전 확인: Python 3.12.15에서 Ruff 검사와 포맷 검사 통과,
pytest 418개 통과(기존 Windows 심볼릭 링크 검사 1개 건너뜀),
Pygbag 0.9.3 양쪽 빌드 성공. 브라우저에서 두 퍼즐의 예제 풀이 완료와
MEOW의 원본 입력 복귀를 확인했다. 원본 Sudoku의 이전 안내 변경도
Ruff 검사와 pytest 63개를 통과했다.
