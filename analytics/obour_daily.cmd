@echo off
rem Run by the Windows scheduled task "Nabta Obour prices". Appends to data\processed\obour_collector.log.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo [%date% %time%] >> ..\data\processed\obour_collector.log
.venv\Scripts\python.exe -m ingest.obour >> ..\data\processed\obour_collector.log 2>&1
.venv\Scripts\python.exe -m commit_snapshots >> ..\data\processed\obour_collector.log 2>&1
if exist ..\.env .venv\Scripts\python.exe -m load obour >> ..\data\processed\obour_collector.log 2>&1 && .venv\Scripts\python.exe -m publish >> ..\data\processed\obour_collector.log 2>&1
