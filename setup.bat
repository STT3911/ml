@echo off
chcp 65001 >nul
echo ============================================================
echo  Установка проекта
echo ============================================================
echo.

echo [1/3] Установка зависимостей...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ОШИБКА: не удалось установить зависимости.
    echo Убедитесь, что Python установлен и доступен в PATH.
    pause
    exit /b 1
)

echo.
echo [2/3] Установка CatBoost (опционально)...
python -m pip install catboost
if errorlevel 1 (
    echo CatBoost не установлен - будет использован RandomForest.
)

echo.
echo [3/3] Обучение всех моделей...
python scripts/train_all.py
if errorlevel 1 (
    echo ОШИБКА: обучение завершилось с ошибкой.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Готово! Все модели и артефакты сохранены в artifacts/
echo ============================================================
pause
