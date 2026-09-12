@echo off
setlocal
if "%~1"=="" goto help
if not defined AGENT_OS_ROOT set "AGENT_OS_ROOT=D:/agent-os"
set "SCR=%AGENT_OS_ROOT%/BASE/scripts"
set "PY=python"
goto dispatch

:dispatch
if /i "%~1"=="init"      goto init
if /i "%~1"=="quickcard" goto quickcard
if /i "%~1"=="sync"      goto sync
if /i "%~1"=="new"       goto new
if /i "%~1"=="run"       goto run
if /i "%~1"=="watch"     goto watch
if /i "%~1"=="evolve"    goto evolve
if /i "%~1"=="doctor"    goto doctor
if /i "%~1"=="archive"   goto notimpl
if /i "%~1"=="help"      goto help
goto help

:new
set "ARGS=%*"
set "ARGS=%ARGS:* =%"
if "%ARGS%"=="%~1" set "ARGS="
%PY% "%SCR%/cmd_new.py" %ARGS%
goto end

:watch
set "ARGS=%*"
set "ARGS=%ARGS:* =%"
if "%ARGS%"=="%~1" set "ARGS="
%PY% "%SCR%/cmd_watch.py" %ARGS%
goto end

:init
set "ARGS=%*"
set "ARGS=%ARGS:* =%"
if "%ARGS%"=="%~1" set "ARGS="
%PY% "%SCR%/cmd_init.py" %ARGS%
goto end

:quickcard
set "ARGS=%*"
set "ARGS=%ARGS:* =%"
if "%ARGS%"=="%~1" set "ARGS="
%PY% "%SCR%/cmd_quickcard.py" %ARGS%
goto end

:sync
set "ARGS=%*"
set "ARGS=%ARGS:* =%"
if "%ARGS%"=="%~1" set "ARGS="
%PY% "%SCR%/cmd_sync.py" %ARGS%
goto end

:run
set "ARGS=%*"
set "ARGS=%ARGS:* =%"
if "%ARGS%"=="%~1" set "ARGS="
%PY% "%SCR%/cmd_run.py" %ARGS%
goto end

:evolve
set "ARGS=%*"
set "ARGS=%ARGS:* =%"
if "%ARGS%"=="%~1" set "ARGS="
%PY% "%SCR%/cmd_evolve.py" %ARGS%
goto end

:doctor
set "ARGS=%*"
set "ARGS=%ARGS:* =%"
if "%ARGS%"=="%~1" set "ARGS="
%PY% "%SCR%/cmd_doctor.py" %ARGS%
goto end

:notimpl
echo [agent-os] "%~1" 未实现（后续 STEP）。已实现：init/quickcard/sync/new/run/watch/evolve/doctor。
goto end

:help
echo agent-os v0.4 原型命令:
echo   agent-os init          冷启动初始化（目录/配置/密钥审计/自测）
echo   agent-os quickcard     打印或生成 REQ 快速卡模板
echo   agent-os new           交互式澄清需求，生成 tasks^<id^>/REQ.md 并登记 registry
echo   agent-os watch         只读汇总所有任务健康
echo   agent-os doctor        只读扫描重复/孤儿/超大/锁冲突，防撞车冗余
echo   agent-os run           单次 dry 执行（只写任务级 task-evolve）
echo   agent-os evolve        任务级轻七阶段常驻（dry，不回 BASE）
echo   agent-os sync          入站同步（默认只读；--apply 需 --yes）
echo   agent-os archive       未实现（后续 STEP）
goto end

:end
endlocal