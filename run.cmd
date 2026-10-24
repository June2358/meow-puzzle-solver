@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
set "PUZZLE_APP=%~1"
if not defined PUZZLE_APP set "PUZZLE_APP=meow"
if /I "%PUZZLE_APP%"=="meow" goto run
if /I "%PUZZLE_APP%"=="sudoku" goto run
echo 사용법: run.cmd [meow^|sudoku]
exit /b 2
:run
pushd "%~dp0" || exit /b 1
where uv >nul 2>nul
if errorlevel 1 goto missing_uv
call uv run --locked --no-dev python -m %PUZZLE_APP%
if errorlevel 1 goto failed
popd
exit /b 0
:missing_uv
echo [오류] uv가 필요합니다. 설치: winget install --id astral-sh.uv -e
:failed
echo [오류] 실행에 실패했습니다. 위 안내를 확인하세요.
echo 계속하려면 아무 키나 누르세요.
pause >nul
popd
exit /b 1
