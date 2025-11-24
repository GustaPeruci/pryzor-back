@echo off
echo Iniciando Pryzor Backend...
cd /d "%~dp0"
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
