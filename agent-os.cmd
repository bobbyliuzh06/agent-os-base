@echo off
setlocal
if "%~1"=="" goto help
if not defined AGENT_OS_ROOT set "AGENT_OS_ROOT=D:/agent-os"
set "SCR=%AGENT_OS_ROOT%/BASE/scripts"
set "PY=python"
goto dispatch

:dispatch
if /i "%~1"=="sync"    goto sync
if /i "%~1"=="new"     goto new
if /i "%~1"=="run"     goto run
if /i "%~1"=="watch"   goto watch
if /i "%~1"=="evolve"  goto evolve
if /i "%~1"=="doctor"  goto doctor
if /i "%~1"=="archive" goto notimpl
if /i "%~1"=="help"    goto help
goto help

:new
shift
%PY% "%SCR%/cmd_new.py" %*
goto end

:watch
shift
%PY% "%SCR%/cmd_watch.py" %*
goto end

:sync
shift
%PY% "%SCR%/cmd_sync.py" %*
goto end

:run
shift
%PY% "%SCR%/cmd_run.py" %*
goto end

:evolve
shift
%PY% "%SCR%/cmd_evolve.py" %*
goto end

:doctor
shift
%PY% "%SCR%/cmd_doctor.py" %*
goto end

:notimpl
echo [agent-os] "%~1" 在 STEP25A 未实现（仅登记）。已实现：new/watch/doctor。
goto end

:help
echo agent-os 原型命令（STEP25A）:
echo   agent-os new     交互式澄清需求，生成 tasks^<id^>/REQ.md 并登记 registry
echo   agent-os watch   只读汇总所有任务健康（无运行数据则提示）
echo   agent-os doctor  只读扫描重复/孤儿/超大/锁冲突，防撞车冗余
echo   agent-os sync/run/evolve/archive  未实现（后续 STEP）
goto end

:end
endlocal