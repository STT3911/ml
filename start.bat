@echo off
chcp 65001 >nul
echo Запуск демо на синтетических данных...
python scripts/run_demo.py --output-dir artifacts/demo
pause
