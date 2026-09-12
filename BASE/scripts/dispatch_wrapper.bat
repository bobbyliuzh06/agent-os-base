@echo off
setlocal enabledelayedexpansion
REM agent-os evolve dispatch: propose + gate + post + cleanup + observe + merge-advice(dry-run) ; no auto apply, no push
set "PYTHON_EXE=python"
set "SCRIPTS=D:/agent-os/BASE/scripts"
set "LOG=D:/agent-os/BASE/regression-runs/dispatch.log"

for /f %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%a"
for /f %%a in ('powershell -NoProfile -Command "Get-Date -Format HH:mm"') do set "NOW=%%a"
echo. >> "%LOG%"
echo ========== [%TODAY% %NOW%] dispatch start ========== >> "%LOG%"

echo [%NOW%] [1/5] propose: evolve_dispatch.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/evolve_dispatch.py" >> "%LOG%" 2>&1
set "RC1=%ERRORLEVEL%"
echo [%NOW%] [1/5] propose rc=%RC1% >> "%LOG%"
if not "%RC1%"=="0" ( echo [%NOW%] [ALERT] propose failed, continue >> "%LOG%" )

echo [%NOW%] [2/5] gate: gate_review_dispatch.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/gate_review_dispatch.py" >> "%LOG%" 2>&1
set "RC2=%ERRORLEVEL%"
echo [%NOW%] [2/5] gate rc=%RC2% >> "%LOG%"

echo [%NOW%] [3/5] postprocess: postprocess_dispatch.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/postprocess_dispatch.py" >> "%LOG%" 2>&1
set "RC3=%ERRORLEVEL%"
echo [%NOW%] [3/5] postprocess rc=%RC3% >> "%LOG%"

echo [%NOW%] [4/5] cleanup+observe+advice >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/cleanup_dispatch.py" >> "%LOG%" 2>&1
set "RC4=%ERRORLEVEL%"
echo [%NOW%] cleanup rc=%RC4% >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/observe_report.py" >> "%LOG%" 2>&1
set "RC5=%ERRORLEVEL%"
echo [%NOW%] observe rc=%RC5% >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/merge_advisor.py" >> "%LOG%" 2>&1
set "RC6=%ERRORLEVEL%"
echo [%NOW%] merge-advice rc=%RC6% >> "%LOG%"

echo [%NOW%] summary: propose_rc=%RC1% gate_rc=%RC2% post_rc=%RC3% cleanup_rc=%RC4% observe_rc=%RC5% advice_rc=%RC6% >> "%LOG%"
if not "%RC1%"=="0" ( echo [ALERT] propose rc=%RC1% >> "%LOG%" )
if not "%RC2%"=="0" ( echo [ALERT] gate rc=%RC2% >> "%LOG%" )
if not "%RC3%"=="0" ( echo [ALERT] post rc=%RC3% >> "%LOG%" )
echo ========== [%TODAY% %NOW%] dispatch end ========== >> "%LOG%"
endlocal