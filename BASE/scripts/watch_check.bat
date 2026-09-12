@echo off
setlocal
if not defined AGENT_OS_ROOT set "AGENT_OS_ROOT=D:/agent-os"
set "BASE=%AGENT_OS_ROOT%"
set "REG=%AGENT_OS_ROOT%\BASE\regression-runs"
set "SCH=AgentOS_EvolveDispatch"
echo ===== %date% %time% agent-os watch =====
echo.
echo [1/4] schtasks
schtasks /Query /TN "%SCH%" /V /FO LIST
echo.
echo [2/4] dashboard STATUS
if exist "%REG%\dashboard.txt" (
  findstr /I "STATUS observe rows all-rc-zero unknown alerts_total accept+low git_sha" "%REG%\dashboard.txt"
) else echo dashboard.txt missing
echo.
echo [3/4] readiness (readonly)
python "%BASE%\BASE\scripts\readiness_eval.py"
echo.
echo [4/4] git sanity (no push/commit)
git -C "%BASE%" log --oneline -3
git -C "%BASE%" status --short
echo.
echo ===== watch end =====
endlocal
call "%~dp0nightly_check.bat"
python "%~dp0posture_check.py" --repo "%AGENT_OS_ROOT%" --out-dir "%AGENT_OS_ROOT%\BASE\regression-runs\posture-daily" >nul 2>&1
