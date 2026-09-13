@echo off
setlocal enabledelayedexpansion
rem agent-os v0.5.1 冷启动初始化（只读检查 + 按需创建目录/模板，不改现有配置）
if not defined AGENT_OS_ROOT (
  set "AGENT_OS_ROOT=%~dp0"
)
rem 归一化：确保末尾有反斜杠，避免拼接出 broken 路径
if not "%AGENT_OS_ROOT:~-1%"=="\" set "AGENT_OS_ROOT=%AGENT_OS_ROOT%\"
set "PY=python"
set "SCR=%AGENT_OS_ROOT%BASE\scripts"

echo ===== agent-os init [%date% %time%] =====
echo AGENT_OS_ROOT=%AGENT_OS_ROOT%
echo.

echo [1/6] python 可用性
%PY% --version
if errorlevel 1 (
  echo [FATAL] 未检测到 python。请先安装 Python 3.10+ 并加入 PATH。
  exit /b 1
)

echo [2/6] 目录结构（按需创建，已存在则跳过）
%PY% -c "import os; [os.makedirs(os.path.join(os.environ['AGENT_OS_ROOT'],d),exist_ok=True) for d in ['BASE\\scripts','BASE\\meta','BASE\\docs','profile\\skills','tasks','BASE\\regression-runs']]"
if errorlevel 1 ( echo [FATAL] 目录创建失败，检查 AGENT_OS_ROOT 权限 & exit /b 1 )

echo [3/6] config.json（不存在才生成模板，绝不覆盖已有配置）
%PY% "%SCR%\cmd_init.py" --ensure-config
if errorlevel 1 ( echo [FATAL] config 初始化失败 & exit /b 1 )

echo [4/6] 密钥来源审计（只读，不打印明文）
%PY% "%SCR%\cmd_init.py" --audit-keys
echo.

echo [5/6] 自测（不触发任何 evolve/调度）
%PY% "%SCR%\cmd_init.py" --selfcheck
echo.

echo [6/6] 完成。下一步：
echo     %AGENT_OS_ROOT%agent-os.cmd help
echo     %AGENT_OS_ROOT%agent-os.cmd new --domain demo --goal try --noninteractive
echo     %AGENT_OS_ROOT%agent-os.cmd doctor
echo ===== init done =====
endlocal