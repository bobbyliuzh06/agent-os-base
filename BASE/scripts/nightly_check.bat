@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0..\.."
if defined AGENT_OS_ROOT ( set "ROOT=%AGENT_OS_ROOT%" )
set "PY=python"
set "OUT=%ROOT%\BASE\regression-runs"
%PY% -c "import os,sys,json,datetime,subprocess,pathlib; root=pathlib.Path(os.environ['ROOT']); os.chdir(str(root)); exec('def run(cmd):\n try:\n  r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)\n  return {\x22rc\x22:r.returncode,\x22out\x22:(r.stdout+r.stderr)[-2000:]}\n except Exception as e:\n  return {\x22rc\x22:-1,\x22out\x22:str(e)}\ndef parse_scan(s):\n try:\n  j=json.loads(s.strip().splitlines()[-1])\n  return j.get(\x22rc\x22,1),int(j.get(\x22hardcoded_d_drive\x22,1)),j.get(\x22rows\x22,-1)\n except Exception:\n  return 1,1,-1'); pytest=run(['python','-m','pytest','tests/','-q']); scan=run(['python',str(root/'BASE/scripts/scan_hardcoded.py'),'--json']); scan_rc,scan_dd,scan_rows=parse_scan(scan['out']); healthy=(pytest['rc']==0 and scan_rc==0 and scan_dd==0); rec={'ts':datetime.datetime.now().isoformat(),'pytest_rc':pytest['rc'],'pytest_out_tail':pytest['out'][-800:],'scan_rc':scan_rc,'scan_hardcoded_d_drive':scan_dd,'scan_rows':scan_rows,'healthy':healthy}; outp=pathlib.Path(os.environ['OUT'])/('nightly-'+datetime.datetime.now().strftime('%%Y%%m%%d')+'.json'); outp.parent.mkdir(exist_ok=True); open(str(outp),'w',encoding='utf-8').write(json.dumps(rec,ensure_ascii=False,indent=2)); print('NIGHTLY rc=%%d healthy=%%s out=%%s'%%(1 if not healthy else 0,healthy,str(outp)))"
if errorlevel 1 ( echo NIGHTLY FAILED & exit /b 1 )
echo NIGHTLY OK
endlocal