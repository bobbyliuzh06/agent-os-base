@echo off
setlocal enabledelayedexpansion
REM agent-os evolve dispatch v0.3: pre-health gate + propose + gate + post + cleanup + observe + advice + post-health/dashboard
set "PYTHON_EXE=python"
if not defined AGENT_OS_ROOT set "AGENT_OS_ROOT=D:/agent-os"
set "SCRIPTS=%AGENT_OS_ROOT%\BASE\scripts"
set "LOG=%AGENT_OS_ROOT%\BASE\regression-runs\dispatch.log"

for /f %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%a"
for /f %%a in ('powershell -NoProfile -Command "Get-Date -Format HH:mm"') do set "NOW=%%a"
echo. >> "%LOG%"
echo ========== [%TODAY% %NOW%] dispatch start ========== >> "%LOG%"

echo [%NOW%] [0/7] pre-health gate >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/health_check.py" pre >> "%LOG%" 2>&1
set "RCH=%ERRORLEVEL%"
echo [%NOW%] pre-health rc=%RCH% >> "%LOG%"
if not "%RCH%"=="0" (
  echo [%NOW%] [ABORT] hard health check failed, skip this round >> "%LOG%"
  echo ========== [%TODAY% %NOW%] dispatch end ^(aborted^) ========== >> "%LOG%"
  endlocal
  exit /b 1
)

echo [%NOW%] [1/7] propose: evolve_dispatch.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/evolve_dispatch.py" >> "%LOG%" 2>&1
set "RC1=%ERRORLEVEL%"
echo [%NOW%] [1/7] propose rc=%RC1% >> "%LOG%"
if not "%RC1%"=="0" ( echo [%NOW%] [ALERT] propose failed, continue >> "%LOG%" )

echo [%NOW%] [2/7] gate: gate_review_dispatch.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/gate_review_dispatch.py" >> "%LOG%" 2>&1
set "RC2=%ERRORLEVEL%"
echo [%NOW%] [2/7] gate rc=%RC2% >> "%LOG%"

echo [%NOW%] [3/7] postprocess: postprocess_dispatch.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/postprocess_dispatch.py" >> "%LOG%" 2>&1
set "RC3=%ERRORLEVEL%"
echo [%NOW%] [3/7] postprocess rc=%RC3% >> "%LOG%"

echo [%NOW%] [4/7] cleanup: cleanup_dispatch.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/cleanup_dispatch.py" >> "%LOG%" 2>&1
set "RC4=%ERRORLEVEL%"
echo [%NOW%] [4/7] cleanup rc=%RC4% >> "%LOG%"

echo [%NOW%] [5/7] observe: observe_report.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/observe_report.py" >> "%LOG%" 2>&1
set "RC5=%ERRORLEVEL%"
echo [%NOW%] [5/7] observe rc=%RC5% >> "%LOG%"

echo [%NOW%] [6a/7] project-pain-verify: project_verify_pains.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/project_verify_pains.py" >> "%LOG%" 2>&1
set "RC6A=%ERRORLEVEL%"
echo [%NOW%] [6a/7] project-pain-verify rc=%RC6A% >> "%LOG%"

echo [%NOW%] [6b/7] project-dual-review: project_dual_review.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/project_dual_review.py" >> "%LOG%" 2>&1
set "RC6B=%ERRORLEVEL%"
echo [%NOW%] [6b/7] project-dual-review rc=%RC6B% >> "%LOG%"

echo [%NOW%] [6c/7] project-pain-rollup: project_pain_rollup.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/project_pain_rollup.py" >> "%LOG%" 2>&1
set "RC6C=%ERRORLEVEL%"
echo [%NOW%] [6c/7] project-pain-rollup rc=%RC6C% >> "%LOG%"

echo [%NOW%] [6d/7] project-strategy-pool: project_strategy_pool.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/project_strategy_pool.py" >> "%LOG%" 2>&1
set "RC6D=%ERRORLEVEL%"
echo [%NOW%] [6d/7] project-strategy-pool rc=%RC6D% >> "%LOG%"

echo [%NOW%] [5a/7] project-selfcheck: project_selfcheck.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/project_selfcheck.py" >> "%LOG%" 2>&1
set "RC5A=%ERRORLEVEL%"
echo [%NOW%] [5a/7] project-selfcheck rc=%RC5A% >> "%LOG%"

echo [%NOW%] [5b/7] project-site-gen: project_site_gen.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/project_site_gen.py" >> "%LOG%" 2>&1
set "RC5B=%ERRORLEVEL%"
echo [%NOW%] [5b/7] project-site-gen rc=%RC5B% >> "%LOG%"

echo [%NOW%] [6/7] advice: merge_advisor.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/merge_advisor.py" >> "%LOG%" 2>&1
set "RC6=%ERRORLEVEL%"
echo [%NOW%] [6/7] advice rc=%RC6% >> "%LOG%"

echo [%NOW%] [7/7] post-health + dashboard >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/health_check.py" post >> "%LOG%" 2>&1
set "RCP=%ERRORLEVEL%"
echo [%NOW%] post-health rc=%RCP% >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/dashboard.py" >> "%LOG%" 2>&1
set "RCD=%ERRORLEVEL%"
echo [%NOW%] dashboard rc=%RCD% >> "%LOG%"

echo [%NOW%] [7a/7] project-regression: project_regression.py >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPTS%/project_regression.py" >> "%LOG%" 2>&1
set "RC7A=%ERRORLEVEL%"
echo [%NOW%] [7a/7] project-regression rc=%RC7A% >> "%LOG%"

echo [%NOW%] summary: pre=%RCH% propose=%RC1% gate=%RC2% post=%RC3% cleanup=%RC4% observe=%RC5% selfcheck=%RC5A% sitegen=%RC5B% pverify=%RC6A% preview=%RC6B% painrollup=%RC6C% pool=%RC6D% advice=%RC6% posthealth=%RCP% regression=%RC7A% dashboard=%RCD% >> "%LOG%"
if not "%RC1%"=="0" ( echo [ALERT] propose rc=%RC1% >> "%LOG%" )
if not "%RC2%"=="0" ( echo [ALERT] gate rc=%RC2% >> "%LOG%" )
if not "%RC3%"=="0" ( echo [ALERT] post rc=%RC3% >> "%LOG%" )
echo ========== [%TODAY% %NOW%] dispatch end ========== >> "%LOG%"
endlocal